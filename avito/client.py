import aiohttp
from aiohttp import BasicAuth
from config import AVITO_CLIENT_ID, AVITO_CLIENT_SECRET

BASE_URL = "https://api.avito.ru"

class AvitoAPI:
    def __init__(self, user_id: int):
        self._access_token = None
        self._session = None
        self._user_id = user_id
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Создаёт сессию один раз и переиспользует"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                proxy="http://109.237.106.126:11223",
                proxy_auth=aiohttp.BasicAuth("tz551x5EaZ", "auUJePl7lA"),
            )
        return self._session
    
    async def _authenticate(self) -> str:
        """Получает access_token у Avito"""
        session = await self._get_session()
        url = f'{BASE_URL}/token'
        data = {
            "grant_type": "client_credentials",
            "client_id": AVITO_CLIENT_ID,
            "client_secret": AVITO_CLIENT_SECRET,
        }
        async with session.post(url, data=data) as resp:
            resp.raise_for_status()
            token_data = await resp.json()
            self._access_token = token_data["access_token"]
            return self._access_token
        
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Основной метод для запросов. Сам следит за токеном."""
        if not self._access_token:
            await self._authenticate()
        
        session = await self._get_session()
        url = f"{BASE_URL}{endpoint}"

        # Вытаскиваем заголовки, если переданы
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f'Bearer {self._access_token}'

        async with session.request(method, url, headers=headers, **kwargs) as resp:
            if resp.status == 401:
                # Токен протух — обновляем и пробуем ещё раз
                await self._authenticate()
                headers["Authorization"] = f"Bearer {self._access_token}"
                async with session.request(method, url, headers=headers, **kwargs) as resp2:
                    resp2.raise_for_status()
                    return await resp2.json()
            resp.raise_for_status()
            return await resp.json()
    
    async def get_reviews(self, user_id: int, limit: int = 10, offset: int = 0) -> dict:
        return await self._request(
            "GET",
            "/ratings/v1/reviews",
            params={"userId": user_id, "limit": limit, "offset": offset}
        )

    async def close(self):
        """Закрываем сессию при завершении работы"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_item_stats(self, item_ids: list[int], date_from: str, date_to: str) -> dict:
        """Получает статистику по списку объявлений (POST)."""
        return await self._request(
            "POST",
            f"/stats/v1/accounts/{self._user_id}/items",
            json={
                "itemIds": item_ids,
                "dateFrom": date_from,
                "dateTo": date_to,
                "fields": ["uniqViews", "uniqContacts", "uniqFavorites"],
                "periodGrouping": "day"
            }
        )

    async def get_spendings(self, date_from: str, date_to: str) -> dict:
        return await self._request(
            "POST",
            f"/stats/v2/accounts/{self._user_id}/spendings",
            json={
                "dateFrom": date_from,
                "dateTo": date_to,
                "grouping": "day",
                "filter": {},
                "spendingTypes": ["promotion", "presence"]
            }
        )