import redis.asyncio as aioredis
from redis.cluster import RedisCluster
import hashlib 
import json
import pickle 
from typing import Dict, List, Any, Optional


cdef class CacheManager:
    cdef object redis_client 
    cdef int default_ttl
    cdef str redis_host
    cdef int redis_port 
    cdef object redis_cluster

    def __init__(self, redis_host: str = "localhost", redis_port : int = 6379, 
                default_ttl : int = 3600, use_cluster : bool = False, cluster_nodes : list = None):
            self.redis_host = redis_host
            self.redis_port = redis_port
            self.default_ttl = default_ttl
            self.redis_client = None 
            self.redis_cluster = None 


            if use_cluster and cluster_nodes:
                redis_cluster = RedisCluster(
                    host = redis_host,
                    port = redis_port,
                    decode_response = False
                )

    async def connect(self):
        if self.redis_client is None:
            self.redis_client = await aioredis.from_url(
                f"redis://{self.redis_host}:{self.redis_port}",
                encoding="utf-8",
                decode_responses=False
            )

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()


    cdef str _generate_cache_key(self, str method, str url, dict header = None, bytes body = None):
        cdef str key_parts = f"{method}:{url}"
        if header:
            cache_headers = {k.lower(): v for k, v in header.items()
                           if k.lower() in ['accept', 'accept-encoding', 'accept-language']}
            if cache_headers:
                key_parts += f":{json.dumps(cache_headers, sort_keys=True)}"

        if body:
            key_parts += f":{hashlib.md5(body).hexdigest()}"
        return f"cache:{hashlib.sha256(key_parts.encode()).hexdigest()}"


    cpdef str generate_cache_key(self, str method, str url, dict header = None, bytes body = None):
        return self._generate_cache_key(method, url, header, body)
    

    async def get(self, str cache_key) -> Optional[Dict[str, Any]]:
        try:
            if self.redis_cluster:
                data = self.redis_cluster.get(cache_key)
            else:
                data = await self.redis_client.get(cache_key)
            
            if data:
                return pickle.loads(data)
            return None 
        except Exception as e:
            print(f"Cache get error: {e}")
            return None 


    async def set(self, str cache_key, dict response_data, int ttl = -1):
        try:
            if ttl == -1:
                ttl = self.default_ttl

            serialized = pickle.dumps(response_data)
            if self.redis_cluster:
                self.redis_cluster.setex(cache_key, ttl, serialized)
            else:
                await self.redis_client.setex(cache_key, ttl, serialized)

            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    

    async def delete(self, str cache_key) -> bool:
        try:
            if self.redis_cluster:
                return bool(self.redis_cluster.delete(cache_key))
            else:
                return bool(await self.redis_client.delete(cache_key))
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def clear_all(self) -> bool:
        """Clear all cache entries"""
        try:
            if self.redis_cluster:
                # For cluster, we need to iterate through all nodes
                for node in self.redis_cluster.get_nodes():
                    keys = node.redis_connection.keys("cache:*")
                    if keys:
                        node.redis_connection.delete(*keys)
            else:
                cursor = b'0'
                while cursor:
                    cursor, keys = await self.redis_client.scan(
                        cursor=cursor,
                        match=b"cache:*",
                        count=100
                    )
                    if keys:
                        await self.redis_client.delete(*keys)
                    if cursor == b'0':
                        break
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        try:
            if self.redis_cluster:
                total_keys = 0
                for node in self.redis_cluster.get_nodes():
                    keys = node.redis_connection.keys("cache:*")
                    total_keys += len(keys)
                return {
                    "total_keys": total_keys,
                    "cluster_mode": True
                }
            else:
                cursor = b'0'
                total_keys = 0
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match=b"cache:*",
                    count=1000
                )
                total_keys = len(keys)
                
                return {
                    "total_keys": total_keys,
                    "cluster_mode": False
                }
        except Exception as e:
            print(f"Stats error: {e}")
            return {"total_keys": 0, "error": str(e)}