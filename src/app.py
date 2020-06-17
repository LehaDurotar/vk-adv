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

cached_posts = {}
# mode = 0
service_is_working = False


@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event: events.NewMessage.Event):
    markup = [
        [Button.text('Начать рассылку', resize=True)],
        [Button.text('Отписаться от всех групп', resize=True)]]

    await event.respond('Выберете команду', buttons=markup)


@bot.on(events.NewMessage(pattern=re.compile('(?:Начать |Отписаться )')))
async def user_setup_handler(event: events.NewMessage.Event):
    header = 'Список постов не обновляется, скрипт не работает'

    markup = Button.inline('Start service', b'start_service')

    if event.text == 'Начать рассылку':
        if service_is_working:
            header = 'Каждые 10 минут скрипт получает список постов из ленты, ' \
                     'доступных для комментирования:'
            markup = [Button.inline('Start commenting', b'start_commenting'),
                      Button.inline('Stop service', b'stop_service')]

    if event.text == 'Отписаться от всех групп':
        if service_is_working:
            header = 'Тестовая функция, суть работы понятна из названия'
            markup = [Button.inline('Unsubscribe', b'start_unsub'),
                      Button.inline('Stop service', b'stop_service')]

    await event.respond(header, buttons=markup)


if aiohttp:

    async def start_fetching():
        while service_is_working:
            async with aiohttp.ClientSession() as session:
                worker = PostWorker(session, Config.token, Config.client_id)
                cached_posts.clear()
                cached_posts.update(await worker.update_feed())
                print(cached_posts)
                await asyncio.sleep(600)


    async def commenting(message, scope='feed', wall_id=None):
        async with aiohttp.ClientSession() as session:
            worker = PostWorker(session, Config.token, Config.client_id)
            if scope:
                tasks = [asyncio.create_task(worker.start_posting(key, val, message))
                         for key, val in cached_posts.items()]
                await asyncio.wait(tasks, timeout=10)
            else:
                t = list(await worker.get_list_posts_id('wall', wall_id))
                await worker.start_posting(wall_id, t, message)


    @bot.on(events.CallbackQuery(data=re.compile(b'(?:start_|stop_)')))
    async def service_init_handler(event: events.CallbackQuery.Event):
        global service_is_working
        service_init_task = None

        if event.data == b'start_service':
            service_is_working = True
            if service_init_task is None:
                service_init_task = asyncio.create_task(start_fetching())
            await event.respond('Сервис запущен')

        if event.data == b'stop_service':
            service_is_working = False
            if service_init_task and not service_init_task.cancelled():
                service_init_task.cancel()
            await event.respond('Сервис остановлен')

        if event.data == b'start_commenting':
            markup = [[Button.inline('Определенная группа', b'wall')],
                      [Button.inline('Новостная лента', b'feed')]]
            await event.respond('Режим комментирования:', buttons=markup)


    @bot.on(events.CallbackQuery(data=re.compile(b'wall|feed')))
    async def service_execute_handler(event: events.CallbackQuery.Event):
        service_poster_task = None
        if event.data == b'wall':
            loop.create_task(commenting(f'1', 'wall', Config.test_public_id))

        if event.data == b'feed':
            loop.create_task(commenting(f'-1'))


async def main():
    await bot.start(bot_token=Config.tg_api_token)
    await bot.run_until_disconnected()


# Инициализация и старт приложения
if __name__ == '__main__':
    loop.run_until_complete(main())
