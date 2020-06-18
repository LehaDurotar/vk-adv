from src import errors
from typing import List, Dict
from aiohttp import ClientSession

import asyncio


class BaseVkQuery(object):

    """
    Реализует базовые запросы к API интерфейсу Вконтакте.
    Описания работы методов и их параметров взяты с https://api.vk.com/method/
    TODO: написать исключения для отлавливания ошибок в запросах
    """

    def __init__(self, session: ClientSession, token: str, client_id: int):
        self._base = 'https://api.vk.com/method/'
        self.__app_permissions = 0
        self._token = token
        self._client_id = client_id
        self._session = session

    async def _fetch_feed(self, **kw):
        async with self._session.get(
                f'{self._base}/newsfeed.get?filters={kw["filters"]}&'
                f'count={kw["count"]}&access_token={self._token}&v=5.52'
        ) as resp:
            return dict(await resp.json())['response']

    async def _create_comment(self, *args):
        async with self._session.get(
                f'{self._base}/wall.createComment?owner_id={args[0]}&'
                f'post_id={args[1]}&message={args[2]}&'
                f'access_token={self._token}&v=5.52'
        ) as resp:
            if resp.status != 200:
                raise errors.ResponseError()
            return await resp.json()

    async def _fetch_wall(self, *args):
        async with self._session.get(
                f'{self._base}/wall.get?owner_id={args[0]}&'
                f'access_token={self._token}&v=5.52'
        ) as resp:
            return dict(await resp.json())['response']

    async def _del_comment_by_id(self, *args):
        async with self._session.get(
                f'{self._base}/wall.deleteComment?owner_id={args[0]}&'
                f'comment_id={args[1]}&access_token={self._token}&v=5.52'
        ) as resp:
            return await resp.json()

    async def _find_comments_by_id(self, *args):
        async with self._session.get(
                f'{self._base}/wall.getComments?owner_id={args[0]}&'
                f'post_id={args[1]}&access_token={self._token}&v=5.52'
        ) as resp:
            return dict(await resp.json())['response']


class VkRequests(BaseVkQuery):

    def __init__(self, session, token, client_id):
        super(VkRequests, self).__init__(session, token, client_id)

    async def fetch_feed(self, count: int = 50):
        """
        Возвращает данные, необходимые для показа списка новостей для текущего пользователя.
        :param count:
        :return: json объект, интересующие нас поля items[source_id], items[post_id]
        """
        return await self._fetch_feed(filters="post", count=count)

    async def create_comment(self, owner_id: int, post_id: int, message: str) -> int:
        """
        :param owner_id: идентификатор пользователя или сообщества, на чьей стене находится запись, к которой
        необходимо добавить комментарий.
        :param post_id:
        :param message:
        :return: статус-код, опубликован комментарий
        или нет
        """
        return await self._create_comment(owner_id, post_id, message)

    async def get_list_posts_id(self, scope: str = 'feed', owner_id: int = None) -> Dict[int, List[int]]:
        """
        Возвращает id постов с опредленной стены или из новостной ленты текущего пользователя
        :param scope: по-умолчанию сканируется новостная лента, wall -
        :param owner_id:
        :return: массив целых чисел
        """
        if scope not in ['feed', 'wall']:
            raise errors.AppScopeError()
        elif scope == 'feed':
            source = dict(await self.fetch_feed())['items']
            return {post['source_id']: [post['post_id']] for post in source}
        # else:
            # return [item["id"] for item in dict(await self.fetch_wall(owner_id))["items"]

    async def fetch_wall(self, owner_id: int):
        return await self._fetch_wall(owner_id)

    async def find_comments_by_id(self, owner_id: int, post_id: int) -> List[int]:
        comments = await self._find_comments_by_id(owner_id, post_id)
        return [row["id"] for row in comments["items"]]


class PostWorker(VkRequests):

    def __init__(self, session, token, client_id):
        """
        :param session: см. https://docs.aiohttp.org/en/stable/client_reference.html#client-session
        :param token: Ключ доступа пользователя (vk access token)
        :param client_id: Идентификатор вашего приложения. Должно быть Standalone с правами доступа: wall, friends
        """
        super(PostWorker, self).__init__(session, token, client_id)

    async def update_feed(self, mode: int = 0, timeout=600, count_posts: int = 50) -> Dict[int, List[int]]:
        return await self.get_list_posts_id(scope='feed')

    async def start_posting(self, owner_id: int, posts_id: List[int], message: str):
        res = await asyncio.gather(
            *[self.create_comment(owner_id, post, message) for post in posts_id]
        )
        return res

    async def delete_comments(self, owner_id: int, posts_id: List[int], wall: str = None):
        # TODO: работает некорректно
        comments = [i for j in posts_id for i in await self.find_comments_by_id(owner_id, j)]
        tasks = [asyncio.create_task((self._del_comment_by_id(comment)) for comment in comments)]
        res = await asyncio.wait(tasks, timeout=1)
        return res
