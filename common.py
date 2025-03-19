import os
import asyncio


def split_dict(original_dict, chunk_size=15) -> list:
    """
    Разделение словарей на части
    :param original_dict: словарь
    :param chunk_size: размер части
    :return:
    """
    items = list(original_dict.items())
    return [
        dict(items[i:i + chunk_size])
        for i in range(0, len(items), chunk_size)
    ]


def check_group_files(file_list, folder_path, max_group_size_mb=50, max_files_per_group=10) -> dict:
    """
    Разделение списка файлов по необходимому размеру для отправки
    :param file_list: список файлов
    :param folder_path: папка с файлами
    :param max_group_size_mb: максимальный размер группы файлов
    :param max_files_per_group: максимальное число файлов в группе
    :return:
    """
    max_group_size_bytes = max_group_size_mb * 1024 * 1024
    found_files, lost_files, large_files, sum_files = [], 0, 0, 0

    # Проверка файлов
    for filename in file_list:
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            lost_files += 1
            continue
        file_size = os.path.getsize(file_path)
        if file_size > max_group_size_bytes:
            large_files += 1
            continue
        found_files.append((filename, file_size))
        sum_files += 1

    # Группировка файлов по размеру файлов и максимальному числу в сообщении
    grouped_files, current_group, current_group_size = [], [], 0
    for filename, size in found_files:
        if (len(current_group) < max_files_per_group) and (current_group_size + size <= max_group_size_bytes):
            current_group.append(filename)
            current_group_size += size
        else:
            if current_group:
                grouped_files.append(current_group)
            # Начинаем новую группу
            current_group = [filename]
            current_group_size = size

    # Добавляем последнюю группу
    if current_group:
        grouped_files.append(current_group)

    return {
        'grouped_files': grouped_files,
        'lost_files': lost_files,
        'large_files': large_files,
        'sum_files': sum_files
    }


async def delete_file(file_path):
    """
    Удаление файла
    """
    if os.path.isfile(file_path):
        os.remove(file_path)

async def delete_files(grouped_files, folder_path):
    """
    Удаление файлов по списку с группами файлов
    """
    tasks = []
    for group_files in grouped_files:
        for filename in group_files:
            file_path = os.path.join(folder_path, filename)
            tasks.append(delete_file(file_path))

    # Запускаем асинхронно
    await asyncio.gather(*tasks)


def clear_dir(dir: str):
    """
    Очистка папок с временными файлами
    """
    # список файлов для очистки
    files = os.listdir(dir)
    for file in files:
        # удаление всех файлов кроме системных гиткип
        if 'gitkeep' not in file:
            os.remove(f'{dir}/{file}')
