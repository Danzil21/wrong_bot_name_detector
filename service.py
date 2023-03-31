import contextlib
import aiohttp
import asyncio
from aiohttp import web
import re
import pymorphy2
import spacy
import Levenshtein
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=5)

SERVER_HOST = "localhost"
SERVER_PORT = 3099

# Инициализируем анализаторы морфологии
morph_ru = pymorphy2.MorphAnalyzer()
nlp_en = spacy.load("en_core_web_sm")

# Добавляем ключевые слова на нужных языках
forbidden_keywords = [
    "администрация", "admin", "notification", "telegram",
    "паведамленне", "адміністрацыя", "тэлеграма", "notify", "mail",
    "хабарландыру", "әкімшілік", "телеграм", "телега", "тон", "ton", "fragment", "фрагмент",
    "повідомлення", "адміністрація", "телеграма", "телеграм", "телеграмм", "рекомендации",
    "избранное", "оповещение", "уведомление", "уведомления"
]


def detect_forbidden_bot_name(bot_name: str, max_distance: int = 1) -> bool:
    # Разделяем имя бота на слова
    words = re.findall(r'\w+', bot_name.lower())

    # Проходимся по каждому слову и ищем совпадения с ключевыми словами
    for word in words:
        # Для русских и украинских слов
        if any(char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюяґєіїйклмнопрстуфхцчшщьюя" for char in word):
            parsed_word = morph_ru.parse(word)[0].normal_form

            for keyword in forbidden_keywords:
                if Levenshtein.distance(parsed_word, keyword) <= max_distance:
                    return True

        # Для английских слов
        elif any(char in "abcdefghijklmnopqrstuvwxyz" for char in word):
            token = nlp_en(word)[0]
            lemma = token.lemma_

            for keyword in forbidden_keywords:
                if Levenshtein.distance(lemma, keyword) <= max_distance:
                    return True

    return False


async def handler(request: aiohttp.request):
    data = await request.post()
    name = data.get('name')
    loop = asyncio.get_event_loop()
    is_forbidden = await loop.run_in_executor(executor, detect_forbidden_bot_name, name, 1)
    return web.Response(text=str(is_forbidden))


async def router():
    service_app = web.Application()
    service_app.add_routes([web.post('/path/', handler)])
    runner = web.AppRunner(service_app)
    await runner.setup()
    site = web.TCPSite(runner, SERVER_HOST, SERVER_PORT)
    await site.start()
    while True:
        await asyncio.sleep(5)


if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt, SystemExit):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(router())