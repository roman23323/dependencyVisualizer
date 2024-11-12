import argparse
import subprocess

import requests
from bs4 import BeautifulSoup

def find_pkg_catalog(url, pkg_name):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Не удалось получить содержимое каталога: {response.status_code}")

    # Используем BeautifulSoup для парсинга HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    letter_catalog = ""
    # Ищем все ссылки на файлы в каталоге
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and href.startswith(pkg_name[0:4]):
            letter_catalog = url + href  # Возвращаем полный URL к каталогу
            break
    if letter_catalog == "":
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and href.startswith(pkg_name[0]):
                letter_catalog = url + href # Возвращаем полный URL к каталогу
                break
    if letter_catalog == "":
        return
    response = requests.get(letter_catalog)
    if response.status_code != 200:
        raise Exception(f"Не удалось получить содержимое каталога: {response.status_code}")

    # Используем BeautifulSoup для парсинга HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and href.startswith(pkg_name):
            return letter_catalog + href
        elif href and href.startswith(pkg_name.split('-')[0]):
            return letter_catalog + href

def find_dsc_file(url):
    """Находит файл .dsc в указанном каталоге."""
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Не удалось получить содержимое каталога: {response.status_code}")

    # Используем BeautifulSoup для парсинга HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Ищем все ссылки на файлы в каталоге
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and href.endswith('.dsc'):
            return url + '/' + href  # Возвращаем полный URL к файлу .dsc

    raise Exception("Файл .dsc не найден в каталоге.")


def get_dsc_file(url):
    """Получает файл .dsc по указанному URL."""
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Не удалось получить файл: {response.status_code}")
    return response.text


def extract_build_dependencies(dsc_content):
    """Извлекает зависимости сборки из содержимого файла .dsc."""
    dependencies = []
    for line in dsc_content.splitlines():
        if line.startswith("Build-Depends:"):
            deps = line[len("Build-Depends:"):].strip().split(",")
            dependencies = [dep.strip().split(" ")[0] for dep in deps]  # Убираем версии
            break
    return dependencies

def create_mermaid_graph(mermaid_content, pkg_name, dependencies):
    if mermaid_content == "":
        mermaid_content = "graph TD;"
    for dependency in dependencies:
        mermaid_content += f"\n    {pkg_name} --> {dependency}"
    return mermaid_content

def main():
    parser = argparse.ArgumentParser(description='Визуализатор графа зависимостей пакетов Ubuntu.')
    parser.add_argument('visualizer_path', help='Путь к программе для визуализации графов.')
    parser.add_argument('package_name', help='Имя анализируемого пакета.')
    parser.add_argument('max_depth', type=int, help='Максимальная глубина анализа зависимостей.')
    parser.add_argument('repository_url', help='URL-адрес репозитория.')

    args = parser.parse_args()

    # URL к каталогу пакета
    url = args.repository_url
    # Максимальная глубина
    depth = args.max_depth

    try:
        dsc_url = find_dsc_file(url)
        print(f"Найден файл .dsc: {dsc_url}")

        dsc_content = get_dsc_file(dsc_url)
        dependencies = extract_build_dependencies(dsc_content)
        mermaid_content = ""
        mermaid_content = create_mermaid_graph(mermaid_content, args.package_name, dependencies)

        while depth > 1:
            new_dependencies = []
            for dependency in dependencies:
                url_main = "http://archive.ubuntu.com/ubuntu/pool/main/"
                url = find_pkg_catalog(url_main, dependency)
                if url is None:
                    continue
                dsc_url = find_dsc_file(url)
                dsc_content = get_dsc_file(dsc_url)
                dependencies = extract_build_dependencies(dsc_content)
                new_dependencies += dependencies
                mermaid_content = create_mermaid_graph(mermaid_content, dependency, dependencies)
                depth -= 1
            dependencies = new_dependencies

        with open("graph.mnd", 'w') as file:
            file.write(mermaid_content)

        subprocess.run([args.visualizer_path, '-i', 'graph.mnd', '-o', 'graph.svg'])

        print(f"Зависимости: {mermaid_content}")
    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
