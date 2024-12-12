import subprocess
import os


def run_visualizer(package_name, depth, visualizer_path, expected_svg):
    # Формируем команду для запуска visualizer.py
    command = [
        'python3', 'visualizer.py', visualizer_path, package_name, str(depth), 'url'
    ]

    # Запускаем команду
    subprocess.run(command)

    # Проверяем, существует ли созданный файл
    if not os.path.exists("graph.svg"):
        print("Выходной файл не был создан.")
        return False

    # Сравниваем с эталонным файлом
    with open("graph.svg", 'rb') as output_file, open(expected_svg, 'rb') as expected_file:
        if output_file.read() == expected_file.read():
            print(f"Тест для {package_name} прошел успешно.")
            return True
        else:
            print(f"Тест для {package_name} не удался. Файлы различаются.")
            return False


if __name__ == "__main__":
    # Параметры для тестирования
    tests = [
        ("curl", 5, "mmdc", "curl.svg"),
        ("python3", 3, "mmdc", "python3.svg"),
        ("eog", 2, "mmdc", "eog.svg"),
    ]

    # Запускаем тесты
    for package_name, depth, visualizer_path, expected_svg in tests:
        run_visualizer(package_name, depth, visualizer_path, expected_svg)
