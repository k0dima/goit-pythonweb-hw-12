from fastapi import Request
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis:
    """Return the Redis client created for the application lifespan.

    Args:
        request (Request): Current HTTP request.

    Returns:
        Redis: Shared asynchronous Redis client.
    """
    return request.app.state.redis
