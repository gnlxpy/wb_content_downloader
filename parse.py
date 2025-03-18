import traceback
import ssl
import certifi
import time
import undetected_chromedriver as uc
from  undetected_chromedriver import ChromeOptions
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
import asyncio
from common import check_group_files, split_dict
from downloader import main_downloader


def get_page_html(url: str) -> bool | str | None:
    """
    Функция получения html страницы
    :param url: ссылка
    :return:
    """
    # инициализируем драйвер selenium
    try:
        options = ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = uc.Chrome(headless=True, browser_executable_path='/usr/local/bin/chrome',
                           driver_executable_path='/opt/wb_content_downloader/chromedriver',
                           version_main=134, options=options)

        print('driver', driver)
    except Exception:
        traceback.print_exc()
        return False
    try:
        # загружаем страницу
        driver.get(url)
        time.sleep(10)
        driver.implicitly_wait(10)

        state = driver.execute_script("return document.readyState;")
        if state == "complete":
            print("HTML loaded")
        else:
            print(f"HTML not loaded, state: {state}")

        sorting_checkbox = driver.find_elements(By.CLASS_NAME, 'sorting__count')
        sorting_checkbox[1].click()
        time.sleep(2)

        # Получаем начальную позицию
        last_height = driver.execute_script("return document.body.scrollHeight")

        # Прокручиваем страницу и проверяем, изменился ли размер страницы
        while True:
            # Прокручиваем страницу вниз с помощью JavaScript
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Ждем, чтобы новые элементы успели загрузиться
            time.sleep(1.5)
            # Получаем новую высоту страницы
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height  # Обновляем высоту страницы

        # делаем паузу и получаем код страницы
        time.sleep(2)
        page_html = driver.page_source
        return page_html
    except Exception:
        traceback.print_exc()
        return False
    finally:
        driver.quit()


def edit_soup(page_html) -> tuple[dict, int] | bool:
    """
    Обработка полученного html для для формирования списка объектов к загрузке
    :param page_html: html страницы с объектами
    :return:
    """
    # получаем html код
    soup = BeautifulSoup(page_html, "html.parser")
    # получаем комментарии пользователй
    comments_list_obj = soup.find_all('li', class_='comments__item feedback product-feedbacks__block-wrapper')
    if not comments_list_obj:
        return False

    files_dict, errors_url = {}, 0
    # перебираем комментарии в коде
    for comment_obj in comments_list_obj:
        # поиск имени
        name_obj = comment_obj.find('meta', itemprop='author')
        name = name_obj.get("content").replace(' ', '-')

        # поиск рейтинга
        star_obj = comment_obj.find('span', class_=re.compile(r"feedback__rating.*stars-line.*star\d"))
        star = star_obj.get('class')[-1] if star_obj else None

        # поиск даты
        date_obj = comment_obj.find('div', class_='feedback__date')
        date = date_obj.text if date_obj else None
        replace_dict = {
            ' • Дополнен': '',
            ', ': '',
            ' ': '',
            ':': '-'
        }
        for key, value in replace_dict.items():
            date = date.replace(key, value)

        # поиск ссылки
        url_obj = comment_obj.find('img', alt="video preview")
        url = url_obj.get('src').replace('/preview.webp', '') if url_obj else None

        # формируем название файла
        file_name = f'{name}_{star}_{date}.mp4'
        if url is not None:
            files_dict[file_name] = url
        else:
            errors_url += 1
    if len(files_dict) == 0:
        return False
    return files_dict, errors_url


def main_parsing_task(message: str):
    """
    Основная задача парсинга
    :param message: сообщение со ссылкой
    :return: словарь с результатами парсинга
    """
    # получение html страницы
    page_html = get_page_html(message)
    if page_html is False:
        return False

    # получение ссылок на ролики
    files_dict, errors_url = edit_soup(page_html)
    if not files_dict:
        return False
    if len(files_dict) > 100:
        return None
    print('Собрано отзывов ', len(files_dict))
    print('files_dict', files_dict)

    # разделение на группы скачивания и запуск асинхронного скачивания роликов
    files_dict_splitted = split_dict(files_dict)
    for files_split in files_dict_splitted:
        result = asyncio.run(main_downloader(files_split))

    # проверка файлов с выявлением ошибок и формирование списка выгрузки для тг
    time.sleep(1)
    result = check_group_files(files_dict.keys(), './downloads')
    result['errors_url'] = errors_url
    return result


if __name__ == '__main__':
    pass
