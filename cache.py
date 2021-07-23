import aioredis
from time import time
from typing import Optional, Tuple

class Cache:
    def __init__(self, connection_url):
        self._redis = aioredis.from_url(connection_url)
    
    async def exists(self, page) -> bool:
        """ Returns True if page `page` exists in the cache. """
        return bool(await self._redis.exists(page))
    
    async def has_expired(self, page) -> bool:
        """ Returns True if page `page` has expired in the cache. """
        return await self._redis.hget(page, "expires") > int(time())
    
    async def set(self, page, body, expires_in=30) -> None:
        """ Sets the page body `body` at page `page`. Expires after `expires_in` seconds. """
        await self._redis.hmset(page, {
            "body": body,
            "expires": int(time()) + expires_in
        })
    
    async def get_body_expired(self, page) -> Tuple[Optional[str], bool]:
        """ Returns the page body, or None if expired, and whether the page has expired or not. """
        body, expires = await self._redis.hmget(page, [
            "body",
            "expires"
        ])
        
        if int(time()) > expires:
            return None, True
        else:
            return body, False
        
