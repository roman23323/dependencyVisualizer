import argparse
import re
import subprocess
from datetime import datetime
from pprint import pprint

import requests
from bs4 import BeautifulSoup


def remove_version(pkg_name):
    """Удаляет номер версии из названия пакета."""
    # Регулярное выражение для поиска версии в конце строки
    return re.sub(r'(-\d[\d.]*(-\d+)?)$', '', pkg_name)


def find_pkg_catalog(url, pkg_name):
    pkg_name = remove_version(pkg_name)  # Убираем версию из названия пакета
    if pkg_name.endswith("-dev"):  # Убираем с конца названия пакета "-dev"
        pkg_name = pkg_name[0:-4]

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
                letter_catalog = url + href  # Возвращаем полный URL к каталогу
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
        if href and href == pkg_name + "/":
            return letter_catalog + href

    print(pkg_name, "не найден в каталоге", letter_catalog)

def find_latest_dsc_file(url):
    """Находит самый новый файл .dsc в указанном каталоге."""
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Не удалось получить содержимое каталога: {response.status_code}")

    # Используем BeautifulSoup для парсинга HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    latest_file = None
    latest_date = None

    # Ищем все строки таблицы
    for row in soup.find_all('tr'):
        # Находим все ячейки в строке
        cells = row.find_all('td')
        if len(cells) < 3:  # Убедимся, что есть хотя бы три ячейки
            continue

        # Получаем ссылку на файл .dsc
        link = cells[1].find('a')
        if link and link['href'].endswith('.dsc'):
            file_url = link['href']  # Получаем URL файла
            # Получаем дату из третьего <td>
            date_str = cells[2].text.strip()  # Извлекаем текст и убираем лишние пробелы

            # Преобразуем строку даты в объект datetime
            try:
                file_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')  # Убедитесь, что формат даты правильный
            except ValueError:
                continue  # Пропускаем, если не удалось преобразовать дату

            # Сравниваем даты
            if latest_date is None or file_date > latest_date:
                latest_date = file_date
                latest_file = file_url

    if latest_file:
        return url + "/" + latest_file
    else:
        raise Exception("Файл .dsc не найден в каталоге.")

# Пример использования
url = 'http://archive.ubuntu.com/ubuntu/pool/main/'  # Замените на нужный URL
try:
    latest_dsc_file = find_latest_dsc_file(url)
    print(f"Самый новый файл .dsc: {latest_dsc_file}")
except Exception as e:
    print(e)


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
        visited_packages = [args.package_name] # Для исключения дублирования, запоминаем посещённые пакеты
        dsc_url = find_latest_dsc_file(url)
        print(f"Найден файл .dsc: {dsc_url}")

        dsc_content = get_dsc_file(dsc_url)
        dependencies = extract_build_dependencies(dsc_content)
        mermaid_content = ""
        mermaid_content = create_mermaid_graph(mermaid_content, args.package_name, dependencies)

        while depth > 1:
            new_dependencies = []
            print(depth)
            pprint(dependencies)
            for dependency in dependencies:
                if dependency in visited_packages:
                    continue
                visited_packages.append(dependency)
                url_main = "http://archive.ubuntu.com/ubuntu/pool/main/"
                url = find_pkg_catalog(url_main, dependency)
                if url is None:
                    continue
                dsc_url = find_latest_dsc_file(url)
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
