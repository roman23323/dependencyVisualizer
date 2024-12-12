import argparse
import subprocess

def get_package_dependencies(package_name):
    command = f"apt-cache depends {package_name}"
    try:
        # Запускаем команду в терминале WSL
        result = subprocess.run(command, capture_output=True, text=True, check=True, shell=True)
        dependencies = result.stdout

        # Обрабатываем вывод, чтобы оставить только зависимости
        dep_lines = dependencies.splitlines()
        filtered_deps = [line for line in dep_lines if line.startswith('  Depends:')]

        # Извлекаем только названия зависимостей, удаляя спец. символы
        return [dep.split('Depends: ')[1].strip("<>") for dep in filtered_deps]

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
        print(f"Вывод ошибки: {e.stderr}")
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Визуализатор графа зависимостей пакетов Ubuntu.')
    parser.add_argument('visualizer_path', help='Путь к программе для визуализации графов.')
    parser.add_argument('package_name', help='Имя анализируемого пакета.')
    parser.add_argument('max_depth', type=int, help='Максимальная глубина анализа зависимостей.')
    parser.add_argument('repository_url', help='URL-адрес репозитория.')
    args = parser.parse_args()

    depth = args.max_depth  # Получаем глубину
    packages_to_visit = [args.package_name]  # Массив пакетов для посещения на текущей итерации
    packages_next = []  # Массив для посещаемых на след. итерации пакетов
    packages_visited = []  # Массив для посещённых пакетов
    mermaid_content = "graph TD;"  # Переменная для содержимого графа
    for i in range(depth):
        while packages_to_visit:
            package = packages_to_visit.pop()  # Извлекаем очередной пакет
            if package in packages_visited:  # Если пакет уже был посещён, пропустим его
                continue
            packages_visited.append(package)  # Относим его к посещённым пакетам
            dependencies = get_package_dependencies(package)  # Получаем зависимости пакета
            for dependency in dependencies:  # Цикл по зависимостям
                packages_next.append(dependency)  # Посетим этот пакет на следующей итерации
                mermaid_content += f'\n   {package} --> {dependency}'  # Вносим запись о зависимости
        packages_to_visit += packages_next  # Обновляем список новыми пакетами
        packages_next.clear()  # Очищаем массив для следующей итерации
    with open("graph.mnd", 'w') as file:  # Запись результата в файл
        file.write(mermaid_content)
    subprocess.run([args.visualizer_path, '-i', 'graph.mnd', '-o', 'graph.svg'])  # Запускаем визуализатор
