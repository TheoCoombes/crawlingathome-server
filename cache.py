import asyncio
import aioredis
from os import getpid
from time import time
from typing import Optional, Tuple
from config import PAGE_CACHE_EXPIRY

class _PageCache:
    def __init__(self, client: aioredis.client.Redis):
        self._redis = client
    
    async def exists(self, page) -> bool:
        """ Returns True if page `page` exists in the cache. """
        return bool(await self._redis.exists(page))
    
    async def has_expired(self, page) -> bool:
        """ Returns True if page `page` has expired in the cache. """
        return await self._redis.hget(page, "expires") > int(time())
    
    async def set(self, page, body) -> None:
        """ Sets the page body `body` at page `page`. Expires after `config.PAGE_CACHE_EXPIRY` seconds. """
        await self._redis.hmset(page, {
            "body": body,
            "expires": int(time() + PAGE_CACHE_EXPIRY)
        })
    
    async def get_body_expired(self, page) -> Tuple[Optional[str], bool]:
        """ Returns the page body, or None if expired, and whether the page has expired or not. """
        body, expires = await self._redis.hmget(page, [
            "body",
            "expires"
        ])
        
        if int(time()) > int(expires):
            return None, True
        else:
            return body, False
        
class Cache:
    def __init__(self, connection_url: str):
        """ Creates the Redis client instance as well as a `_PageCache` instance for caching webpages. """
        self.client = aioredis.utils.from_url(connection_url)
        self.page = _PageCache(self.client)
    
    async def initPID(self, sleep: bool = True) -> int:
        """ Gets the current process ID, and pushes it to the Redis `workers` list. """
        self.pid = getpid()
        await self.client.rpush("workers", pid)
        
        if sleep:
            await asyncio.sleep(0.25)
            
        self.worker = await self.client.lpos("workers", self.pid)
        return self.worker
    
    async def safeExit(self) -> None:
        """ [IMPORTANT] Resets the workers list to allow the server to
                                        safely turn back on again. """
        await self.client.delete("workers")
