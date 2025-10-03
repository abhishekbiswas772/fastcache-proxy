#!/usr/bin/env env python3

import click
import asyncio
from src.cache_manager import CacheManager
from src.load_balancer import LoadBalancer
from src.server import Server
from src.balance_strategy import BalancingStrategy
from src.proxy_server import CachingProxyServer

@click.group()
def cli():
    """Caching Proxy Server - Cache responses from origin servers"""
    pass


@cli.command()
@click.option('--port', '-p', type=int, required=True, help='Port to run the proxy server on')
@click.option('--origin', '-o', type=str, required=True, help='Origin server URL')
@click.option('--redis-host', default='localhost', help='Redis host')
@click.option('--redis-port', default=6379, type=int, help='Redis port')
@click.option('--cache-ttl', default=3600, type=int, help='Cache TTL in seconds')
@click.option('--use-cluster', is_flag=True, help='Use Redis cluster')
@click.option('--load-balance', is_flag=True, help='Enable load balancing')
@click.option('--servers', multiple=True, help='Backend servers for load balancing (format: name:weight)')
@click.option('--strategy', 
              type=click.Choice(['round-robin', 'weighted-round-robin', 'random', 'weighted-random', 'least-connections']),
              default='weighted-round-robin',
              help='Load balancing strategy')
def start(port, origin, redis_host, redis_port, cache_ttl, use_cluster, load_balance, servers, strategy):
    """Start the caching proxy server"""
    
    click.echo(f"Starting caching proxy server on port {port}")
    click.echo(f"Origin server: {origin}")
    click.echo(f"Redis: {redis_host}:{redis_port} (Cluster: {use_cluster})")
    click.echo(f"Cache TTL: {cache_ttl} seconds")
    
    # Initialize cache manager
    cache_manager = CacheManager(
        redis_host=redis_host,
        redis_port=redis_port,
        default_ttl=cache_ttl,
        use_cluster=use_cluster
    )
    
    # Initialize load balancer if enabled
    load_balancer = None
    if load_balance and servers:
        strategy_map = {
            'round-robin': BalancingStrategy.ROUND_ROBIN,
            'weighted-round-robin': BalancingStrategy.WEIGHTED_ROUND_ROBIN,
            'random': BalancingStrategy.RANDOM,
            'weighted-random': BalancingStrategy.WEIGHTED_RANDOM,
            'least-connections': BalancingStrategy.LEAST_CONNECTIONS
        }
        
        server_list = []
        for server_str in servers:
            parts = server_str.split(':')
            name = parts[0]
            weight = int(parts[1]) if len(parts) > 1 else 1
            server_list.append(Server(name, weight))
        
        load_balancer = LoadBalancer(server_list, strategy_map[strategy])
        click.echo(f"Load balancing enabled with {len(server_list)} servers using {strategy} strategy")
    
    # Create and run proxy server
    proxy = CachingProxyServer(
        port=port,
        origin=origin,
        cache_manager=cache_manager,
        load_balancer=load_balancer
    )
    
    try:
        proxy.run()
    except KeyboardInterrupt:
        click.echo("\nShutting down server...")


@cli.command()
@click.option('--redis-host', default='localhost', help='Redis host')
@click.option('--redis-port', default=6379, type=int, help='Redis port')
@click.option('--use-cluster', is_flag=True, help='Use Redis cluster')
def clear_cache(redis_host, redis_port, use_cluster):
    """Clear all cached data"""
    click.echo("Clearing cache...")
    
    cache_manager = CacheManager(
        redis_host=redis_host,
        redis_port=redis_port,
        use_cluster=use_cluster
    )
    
    async def clear():
        await cache_manager.connect()
        success = await cache_manager.clear_all()
        await cache_manager.close()
        return success
    
    success = asyncio.run(clear())
    
    if success:
        click.echo("✓ Cache cleared successfully")
    else:
        click.echo("✗ Error clearing cache")


@cli.command()
@click.option('--redis-host', default='localhost', help='Redis host')
@click.option('--redis-port', default=6379, type=int, help='Redis port')
@click.option('--use-cluster', is_flag=True, help='Use Redis cluster')
def stats(redis_host, redis_port, use_cluster):
    """Show cache statistics"""
    cache_manager = CacheManager(
        redis_host=redis_host,
        redis_port=redis_port,
        use_cluster=use_cluster
    )
    
    async def get_stats():
        await cache_manager.connect()
        stats = await cache_manager.get_stats()
        await cache_manager.close()
        return stats
    
    stats_data = asyncio.run(get_stats())
    
    click.echo("\n=== Cache Statistics ===")
    click.echo(f"Total cached entries: {stats_data.get('total_keys', 0)}")
    click.echo(f"Cluster mode: {stats_data.get('cluster_mode', False)}")


if __name__ == '__main__':
    cli()