import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InputMediaVideo
from aiogram.types.input_file import FSInputFile
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from common import delete_files
from parse import main_parsing_task


# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TG_TOKEN')
URL_PART_LIST = ['wildberries', 'catalog', 'feedbacks', 'https://']


# инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher()
# запуск второго потока и очереди задач
executor = ThreadPoolExecutor(max_workers=3)
request_queue = asyncio.Queue()


async def background_task():
    """
    Обработчик синхронных задач в отдельном потоке
    """
    while True:
        user_id, message = await request_queue.get()
        print('Задание начато', user_id, message)
        # Запускаем sync задачу в отдельном потоке
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, main_parsing_task, message)
        # Отправляем результат
        await send_response(user_id, result)


@dp.message(CommandStart())
async def start(message: Message):
    """
    Приветственное сообщение
    """
    await message.answer("Привет 👋 \n"
                         "Я могу скачать быстро видео отзывы с сайта WB\n"
                         "Для этого тебе необходимо отправить ссылку на страницу отзывов\n"
                         "Приступим? 🤖")


async def send_response(user_id: int, result: dict | bool) -> None:
    """
    Отправка результата парсинга
    :param user_id: юзер айди
    :param result: словарь с данными сбора
    """
    print('user_id', user_id, 'result', result)
    if result is dict and len(result['grouped_files']) > 0:
        await bot.send_message(chat_id=user_id, text=f"✅Были скачаны {result['sum_files']} файлов\n"
                                                     f"Файлов с ошибками {result['lost_files']}\n"
                                                     f"Не найденные ссылки для скачивания {result['errors_url']}\n"
                                                     f"Слишком больших файлов для отправки - {result['large_files']}\n"
                                                     f"Немного подождите пока происходит передача файлов...")
        # отправка подготовленных списков с файлами
        for _list in result['grouped_files']:
            media = []
            for file in _list:
                media.append(InputMediaVideo(media=FSInputFile(f'./downloads/{file}')))
            await bot.send_media_group(chat_id=user_id, media=media)
        # удаление скачанных и отправленных файлов
        await delete_files(result['grouped_files'], './downloads/')
    if result is None:
        await bot.send_message(user_id, "⛔️ К сожалению тестовая версия программы не собирает более 100 комментариев")
    else:
        await bot.send_message(user_id, "😰 К сожалению данные не были собраны")


@dp.message()
async def handle_message(message: Message) -> None:
    """
    Обработчик всех входящих сообщений
    """
    # получение id и сообщения пользователя
    user_id = message.from_user.id
    user_message = message.text
    # проверка верности ввода ссылки
    check = all(url_part in user_message for url_part in URL_PART_LIST)
    if not check or ' ' in user_message:
        await message.reply("Неверный формат ссылки 😡")
        return
    # Сообщаем пользователю, что запрос принят
    # Отправляем запрос в очередь
    await request_queue.put((user_id, user_message))
    await message.reply("🚀 Ваш запрос обрабатывается\n"
                        "В среднем время ожидания не более 5 минут")


async def main():
    """
    Запуск отдельного потока для обработки задач и тг бота
    """
    asyncio.create_task(background_task())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
