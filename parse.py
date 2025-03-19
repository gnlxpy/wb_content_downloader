import datetime
import os
import traceback
import ssl
import certifi
from dotenv import load_dotenv
from fake_useragent import UserAgent
import time
import undetected_chromedriver as uc
from  undetected_chromedriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import re
import asyncio
from common import check_group_files, split_dict
from downloader import main_downloader


load_dotenv()


ua = UserAgent()
PROXY = os.getenv('PROXY')


def get_page_html(url: str) -> bool | str | None:
    """
    Функция получения html страницы
    :param url: ссылка
    :return:
    """
    # инициализируем драйвер selenium
    try:
        options = ChromeOptions()
        options.add_argument('--incognito')
        options.add_argument('--disable-application-cache')
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-agent={ua.chrome}")
        options.add_argument(f'--proxy-server={PROXY}')

        driver = uc.Chrome(
            headless=True,
            browser_executable_path='/usr/local/bin/chrome',
            driver_executable_path='/opt/wb_content_downloader/chromedriver',
            version_main=134,
            options=options, use_subprocess=False
           )

        driver.set_window_size(1600, 960)

        print('driver', driver)
    except Exception:
        traceback.print_exc()
        return False
    try:
        # загружаем страницу
        driver.get(url)
        time.sleep(25)

        state = driver.execute_script("return document.readyState;")
        if state == "complete":
            print("HTML loaded")
            error_load = 3
            while True:
                try:
                    sorting__count = driver.find_elements(By.CLASS_NAME, 'sorting__count')
                    sorting__count[1].click()
                    break
                except Exception:
                    error_load -= 1
                    if error_load <= 0:
                        print("sorting__count NOT loaded")
                        return False
                    time.sleep(10)
        else:
            print(f"HTML not loaded, state: {state}")

        print("sorting__count clicked")
        time.sleep(5)
        driver.save_screenshot(f'./pages_history/{datetime.datetime.now()}.png')

        # Получаем начальную позицию
        last_height = driver.execute_script("return document.body.scrollHeight")
        # actions = ActionChains(driver)

        # Прокручиваем страницу и проверяем, изменился ли размер страницы
        while True:
            # Прокручиваем страницу вниз с помощью JavaScript
            driver.execute_script("window.scrollBy(0, 250);")
            # Ждем, чтобы новые элементы успели загрузиться
            time.sleep(5)
            print('Page scroll . . .')
            driver.save_screenshot(f'./pages_history/{datetime.datetime.now()}.png')
            # Получаем новую высоту страницы
            new_height = driver.execute_script("return document.body.scrollHeight")
            # делаем проверки загрузки всей страницы
            if new_height == last_height:
                try:
                    driver.find_element(By.XPATH, "//a[@href='/services/o-nas' and text()='О нас']").click()
                    break
                except Exception:
                    continue
            last_height = new_height  # Обновляем высоту страницы
        print('Page scrolled!')
        # делаем паузу и получаем код страницы
        driver.save_screenshot(f'./pages_history/{datetime.datetime.now()}.png')
        time.sleep(5)
        page_html = driver.page_source
        with open(f'./pages_history/page_{datetime.datetime.now().replace(microsecond=0)}.html', 'w') as f:
            f.write(str(page_html))
        return page_html
    except Exception:
        traceback.print_exc()
        return False
    finally:
        driver.quit()


def edit_soup(page_html) -> tuple[dict, int] | tuple[bool, None]:
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
        return False, None

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
        if date is not None:
            for key, value in replace_dict.items():
                date = date.replace(key, value)
        else:
            date = 'non-date'

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
        return False, None
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
    get_page_html('https://www.wildberries.ru/catalog/317653108/feedbacks?imtId=299135624&size=478876299')
