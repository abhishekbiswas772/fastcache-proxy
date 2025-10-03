# Caching Proxy Server

A high-performance HTTP caching proxy server built with Python, Cython, Redis, and aiohttp. Features intelligent caching, load balancing with multiple strategies, and Redis cluster support.

## Features

- ✅ **HTTP Caching**: Cache GET/HEAD requests with configurable TTL
- ✅ **Redis Support**: Single instance or cluster mode
- ✅ **Load Balancing**: 5 strategies (Round-Robin, Weighted Round-Robin, Random, Weighted Random, Least Connections)
- ✅ **High Performance**: Cython-optimized cache and load balancer modules
- ✅ **Async I/O**: Built on aiohttp for concurrent request handling
- ✅ **Cache Management**: CLI commands for stats and cache clearing

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────┐
│   Client    │─────▶│  Caching Proxy   │─────▶│ Origin Server│
└─────────────┘      │  (Port 3000)     │      └──────────────┘
                     └──────────────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │  Redis Cache     │
                     │  (Cluster/Single)│
                     └──────────────────┘
```

## Tech Stack

- **Python 3.10+**
- **Cython**: For performance-critical modules
- **aiohttp**: Async HTTP server/client
- **Redis**: Caching backend (async cluster support)
- **Click**: CLI framework
- **Docker**: Redis deployment

## Installation

### 1. Clone Repository
```bash
git clone <your-repo>
cd caching_proxy
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Build Cython Extensions
```bash
python setup.py build_ext --inplace
```

## Quick Start

### Start Redis
```bash
# Using Docker (easiest)
docker run -d --name redis -p 6379:6379 redis:7.2-alpine

# Or using docker-compose
cd image
docker-compose up -d redis
```

### Start Proxy Server
```bash
python app.py start \
  --port 3000 \
  --origin https://dummyjson.com \
  --redis-host localhost \
  --redis-port 6379 \
  --cache-ttl 3600
```

### Test with curl
```bash
# First request (MISS)
curl -v http://localhost:3000/products/1

# Second request (HIT)
curl -v http://localhost:3000/products/1

# Check X-Cache header: HIT or MISS
```

## CLI Commands

### Start Server
```bash
python app.py start --port 3000 --origin <URL> [OPTIONS]

Options:
  --redis-host TEXT      Redis host (default: localhost)
  --redis-port INT       Redis port (default: 6379)
  --cache-ttl INT        Cache TTL in seconds (default: 3600)
  --use-cluster          Enable Redis cluster mode
  --load-balance         Enable load balancing
  --servers TEXT         Backend servers (format: name:weight)
  --strategy TEXT        Load balancing strategy
```

### Load Balancing Strategies
- `round-robin`: Simple round-robin
- `weighted-round-robin`: Weight-based distribution
- `random`: Random selection
- `weighted-random`: Weighted random selection
- `least-connections`: Route to least busy server

### Example with Load Balancing
```bash
python app.py start \
  --port 3000 \
  --origin https://api.example.com \
  --load-balance \
  --servers server1.example.com:5 \
  --servers server2.example.com:3 \
  --strategy weighted-round-robin
```

### Cache Management
```bash
# View cache statistics
python app.py stats --redis-host localhost --redis-port 6379

# Clear all cache
python app.py clear-cache --redis-host localhost --redis-port 6379
```

## Redis Cluster Setup (Optional)

### 1. Update Config Files
```bash
cd image
# Edit redis-node-*.conf files to set cluster-announce-ip
```

### 2. Start Cluster
```bash
docker-compose up -d
```

### 3. Create Cluster
```bash
docker exec -it redis-node-1 redis-cli --cluster create \
  redis-node-1:7001 redis-node-2:7002 redis-node-3:7003 \
  redis-node-4:7004 redis-node-5:7005 redis-node-6:7006 \
  --cluster-replicas 1 --cluster-yes
```

### 4. Use Cluster
```bash
python app.py start \
  --port 3000 \
  --origin https://dummyjson.com \
  --redis-host localhost \
  --redis-port 7001 \
  --use-cluster
```

## Project Structure

```
caching_proxy/
├── app.py                          # CLI entry point
├── setup.py                        # Cython build config
├── requirements.txt                # Python dependencies
├── src/
│   ├── cache_manager/
│   │   └── cache_manager.pyx       # Cython cache manager
│   ├── load_balancer/
│   │   ├── load_balancer.pyx       # Cython load balancer
│   │   ├── server.pyx              # Server model
│   │   └── balance_strategy.pyx    # Strategy enum
│   └── proxy_server/
│       └── proxy_server.py         # Main proxy server
└── image/
    ├── docker-compose.yml          # Redis cluster config
    └── redis-node-*.conf           # Redis node configs
```

## Cache Key Generation

Cache keys are generated using:
- HTTP Method (GET, HEAD)
- Full URL (including query string)
- Relevant headers (Accept, Accept-Encoding, Accept-Language)
- Request body hash (for POST/PUT)

Example: `cache:sha256(GET:/products/1:{"accept":"application/json"})`

## Performance

- **Cython Optimization**: Cache manager and load balancer compiled to C
- **Async I/O**: Non-blocking request handling
- **Connection Pooling**: Reused HTTP connections
- **Efficient Serialization**: Pickle for fast cache storage

## Response Headers

The proxy adds these headers:
- `X-Cache`: `HIT` or `MISS`
- `X-Cache-Key`: The cache key used

## Development

### Rebuild Cython Modules
```bash
python setup.py build_ext --inplace
```

### Run Tests
```bash
pytest tests/
```

### Code Style
```bash
black src/
ruff check src/
```

## Troubleshooting

### Issue: "Decompression failed"
**Solution**: Clear cache after code changes
```bash
python app.py clear-cache --redis-host localhost --redis-port 6379
```

### Issue: Redis connection timeout
**Solution**: Ensure Redis is running
```bash
docker ps | grep redis
```

### Issue: Port already in use
**Solution**: Kill process on port
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :3000
kill -9 <PID>
```

## Configuration

### Environment Variables
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export CACHE_TTL=3600
export PROXY_PORT=3000
```

### Redis Cluster Config (redis-node-*.conf)
```
port 7001
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly yes
protected-mode no
bind 0.0.0.0
cluster-announce-ip 127.0.0.1
cluster-announce-port 7001
cluster-announce-bus-port 17001
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Roadmap

- [ ] HTTP/2 support
- [ ] Prometheus metrics
- [ ] GraphQL caching
- [ ] Rate limiting
- [ ] Circuit breaker pattern
- [ ] Health checks for backend servers

## Author

Abhishek Biswas

## Acknowledgments

- Built with [aiohttp](https://docs.aiohttp.org/)
- Powered by [Redis](https://redis.io/)
- Optimized with [Cython](https://cython.org/)



The idea for this project from `https://roadmap.sh/projects/caching-server`