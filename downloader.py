import asyncio
from ffmpeg_asyncio import FFmpeg, Progress


async def ffmpeg_exc(file_name: str, url_video: str) -> None:
    """
    Асинхронная версия конвертера видеороликов
    :param file_name: имя файла
    :param url_video: ссылка на плейлист видеоролика
    :return:
    """
    ffmpeg = (
        FFmpeg()
        .input(f"{url_video}/index.m3u8")
        .output(f"./downloads/{file_name}", c="copy")
    )

    @ffmpeg.on("progress")
    def on_progress(progress: Progress):
        # print(f"{id_video}: {progress}")
        pass

    @ffmpeg.on("stderr")
    def on_stderr(line: str):
        if "404 Not Found" in line:
            print(f"❌ Видео {url_video}: .m3u8 файл не найден (404)")

    @ffmpeg.on("completed")
    def completed():
        print(f"{url_video}: Finished!")

    @ffmpeg.on("terminated")
    def exited(return_code: int):
        print(f"{url_video}: Terminated with code {return_code}")
        if return_code == 8:
            raise Exception(f"{url_video}: ffmpeg failed with code 8")

    try:
        # Добавим timeout для страховки
        await asyncio.wait_for(ffmpeg.execute(), timeout=60)
    except asyncio.TimeoutError:
        print(f"{url_video}: Timeout! Killing ffmpeg process...")
        ffmpeg.terminate()
        raise
    except Exception as e:
        print(f"{url_video}: Exception - {e}")
        raise


async def main_downloader(files_dict: dict):
    """
    Основная функция загрузчика/конвертера видеороликов
    :param files_dict:
    :return:
    """
    # создание очереди задач
    tasks = [asyncio.create_task(ffmpeg_exc(file_name, url_video)) for file_name, url_video in files_dict.items()]
    # выполенение пачки задач
    done = await asyncio.gather(*tasks, return_exceptions=True)

    return done


if __name__ == "__main__":
    pass
