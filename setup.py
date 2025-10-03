from setuptools import setup, Extension
from Cython.Build import cythonize
import sys


extensions = [
    Extension(
        "src.cache_manager.cache_manager",
        ["src/cache_manager/cache_manager.pyx"],
        language="c++",
    ),
    Extension(
        "src.load_balancer.load_balancer",
        ["src/load_balancer/load_balancer.pyx"],
        language="c++",
    ),
    Extension(
        "src.load_balancer.server",
        ["src/load_balancer/server.pyx"],
        language="c++",
    ),
    Extension(
        "src.load_balancer.balance_strategy",
        ["src/load_balancer/balance_strategy.pyx"],
        language="c++",
    ),
]

setup(
    name="caching_proxy",
    version="1.0.0",
    description="High-performance caching proxy server with Redis and load balancing",
    author="Your Name",
    packages=[
        "src",
        "src.cache_manager",
        "src.load_balancer",
        "src.proxy_server",
    ],
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': "3",
            'embedsignature': True,
            'binding': True,
        },
        annotate=False,
    ),
    install_requires=[
        "aiohttp",
        "redis",
        "click",
        "Cython",
    ],
    entry_points={
        'console_scripts': [
            'caching-proxy=app:cli',
        ],
    },
    python_requires='>=3.7',
    zip_safe=False,
)
