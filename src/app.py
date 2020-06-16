import logging

from config_parser import Config
from vk_api import PostWorker
from telethon import Button, TelegramClient, events, errors, types

import asyncio
import aiohttp
import tracemalloc
import re

tracemalloc.start()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)
loop = asyncio.get_event_loop()

bot = TelegramClient('admin_broadcast', Config.tg_api_id, Config.tg_api_hash)

posts_id = []
# mode = 0
service_is_working = False


@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event: events.NewMessage.Event):
    markup = [
        [Button.text('Начать рассылку', resize=True)],
        [Button.text('Отписаться от всех групп', resize=True)]]

    await asyncio.wait([
        event.delete(),
        event.respond('Выберете команду', buttons=markup)
    ])


@bot.on(events.NewMessage(pattern=re.compile('(Начать|Отписаться)( )')))
async def user_setup_handler(event: events.NewMessage.Event):
    header = 'Список постов не обновляется, скрипт не работает\nДоступные команды:'

    markup = Button.inline('Start service', b'start_service')

    if event.text == 'Начать рассылку':
        if service_is_working:
            header = 'Каждые 10 минут скрипт получает список постов из ленты, ' \
                     'доступных для комментирования\nДоступные команды:'
            markup = [Button.inline('Start commenting', b'start_commenting'),
                      Button.inline('Stop service', b'stop_service')]

    if event.text == 'Отписаться от всех групп':
        if service_is_working:
            header = 'Тестовая функция, суть работы понятна из названия'
            markup = [Button.inline('Unsubscribe', b'start_unsub'),
                      Button.inline('Stop service', b'stop_service')]

    await asyncio.wait([
        event.delete(),
        event.respond(header, buttons=markup)
    ])


if aiohttp:

    async def start_fetching(worker: PostWorker):
        posts_id.clear()
        posts_id.extend(await worker.update_feed())
        await asyncio.sleep(600)


    @bot.on(events.CallbackQuery())
    async def user_execute_handler(event: events.CallbackQuery.Event):
        global service_is_working, posts_id

        async with aiohttp.ClientSession() as session:
            vk_worker = PostWorker(session, Config.token, Config.client_id)

            if event.data == b'start_service':
                # service_is_working = not service_is_working
                service_is_working = True
                loop.create_task(start_fetching(vk_worker))
                await event.respond(f'Сервис запущен\n{str(posts_id)}')

            if event.data == b'stop_service':
                service_is_working = False
                await event.respond(f'Сервис остановлен')


async def main():
    await bot.start(bot_token=Config.tg_api_token)
    await bot.run_until_disconnected()


# Инициализация и старт приложения
if __name__ == '__main__':
    loop.run_until_complete(main())
