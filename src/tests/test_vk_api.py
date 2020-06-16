import inspect

import pytest

from vk_api import PostWorker
from aiohttp import ClientSession
from config_parser import Config


@pytest.mark.asyncio
async def test_fetch_feed():
    async with ClientSession() as session:
        vk_poster = PostWorker(session, Config.token, Config.client_id)
        print(await vk_poster.update_feed())
