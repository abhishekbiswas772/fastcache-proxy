from src.cache_manager.cache_manager import CacheManager
from src.load_balancer.load_balancer import LoadBalancer
from src.load_balancer.server import Server
from src.load_balancer.balance_strategy import BalancingStrategy
import logging
from typing import Optional
import aiohttp
from aiohttp import web, ClientSession
import asyncio
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress Windows asyncio connection reset errors
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class CachingProxyServer:
    def __init__(self, port: int, origin: str, cache_manager: CacheManager,
                 load_balancer: Optional[LoadBalancer] = None):
        self.port = port
        self.origin = origin.rstrip('/')
        self.cache_manager = cache_manager
        self.load_balancer = load_balancer
        self.app = web.Application()
        self.session: Optional[ClientSession] = None
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0
        }
        
        # Setup routes
        self.app.router.add_route('*', '/{path:.*}', self.handle_request)
        self.app.on_startup.append(self.startup)
        self.app.on_cleanup.append(self.cleanup)


    async def startup(self, app):
        self.session = ClientSession()
        await self.cache_manager.connect()
        logger.info(f"Caching proxy server started on port {self.port}")
        logger.info(f"Forwarding requests to {self.origin}")
    
    async def cleanup(self, app):
        if self.session:
            await self.session.close()
        await self.cache_manager.close()
        logger.info("Server shutdown complete")
    
    def _get_target_url(self, path: str) -> str:
        if self.load_balancer:
            server = self.load_balancer.get_next_server()
            if server and server.is_healthy():
                base_url = f"http://{server.get_name()}"
                server.increment_connections()
                return f"{base_url}/{path}"
        
        return f"{self.origin}/{path}"
    

    async def handle_request(self, request: web.Request) -> web.Response:
        self.stats['total_requests'] += 1
        method = request.method
        path =  request.match_info.get('path', '')
        query_string = request.query_string
        full_path = f"{path}?{query_string}" if query_string else path

        body = await request.read() if request.can_read_body else None 
        cache_key = self.cache_manager.generate_cache_key(
            method,
            full_path,
            dict(request.headers),
            body
        )
        is_cacheable = method in ['GET', 'HEAD']
        if is_cacheable:
            cached_response = await self.cache_manager.get(cache_key)
            if cached_response:
                self.stats['hits'] += 1
                logger.info(f"Cache HIT: {method} /{full_path}")
                
                response = web.Response(
                    body=cached_response['body'],
                    status=cached_response['status'],
                    headers=cached_response['headers']
                )
                response.headers['X-Cache'] = 'HIT'
                response.headers['X-Cache-Key'] = cache_key
                return response
        
        self.stats['misses'] += 1
        logger.info(f"Cache MISS: {method} /{full_path}")
        
        try:
            target_url = self._get_target_url(full_path)
            async with self.session.request(
                method=method,
                url=target_url,
                headers={k: v for k, v in request.headers.items() 
                        if k.lower() not in ['host']},
                data=body,
                allow_redirects=False
            ) as origin_response:
                response_body = await origin_response.read()
                response_headers = dict(origin_response.headers)

                # Remove hop-by-hop headers
                for header in ['Connection', 'Keep-Alive', 'Transfer-Encoding',
                              'TE', 'Trailer', 'Proxy-Authorization', 'Proxy-Authenticate',
                              'Content-Encoding']:
                    response_headers.pop(header, None)

                if is_cacheable and 200 <= origin_response.status < 300:
                    cache_data = {
                        'body': response_body,
                        'status': origin_response.status,
                        'headers': response_headers
                    }
                    await self.cache_manager.set(cache_key, cache_data)
                
                # Create response
                response = web.Response(
                    body=response_body,
                    status=origin_response.status,
                    headers=response_headers
                )
                response.headers['X-Cache'] = 'MISS'
                response.headers['X-Cache-Key'] = cache_key
                
                if self.load_balancer:
                    server = self.load_balancer.get_next_server()
                    if server:
                        server.decrement_connections()
                
                return response
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error forwarding request: {e}")
            return web.Response(
                text=f"Error: {str(e)}",
                status=502,
                headers={'X-Cache': 'ERROR'}
            )
    
    def get_stats(self):
        return {
            **self.stats,
            'hit_rate': (self.stats['hits'] / self.stats['total_requests'] * 100) 
                       if self.stats['total_requests'] > 0 else 0
        }
    
    def run(self):
        web.run_app(self.app, port=self.port)