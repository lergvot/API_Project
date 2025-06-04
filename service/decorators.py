# service/decorators.py
import logging
from functools import wraps

from fastapi import Request

from service.cache import get_cached, set_cached, ttl_logic
from service.config import CACHE_TTL

logger = logging.getLogger(__name__)


def cached_route(
    cache_key: str,
    ttl: int | None = None,
    fallback_data: dict | None = None,
    source: str = "auto",
):
    """
    Кэширует результат функции на время из CACHE_TTL[cache_key] или ttl.
    Если кэш устарел — обновляет и выставляет TTL заново.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            use_cache = request.query_params.get("nocache") != "true"
            if use_cache:
                cached = await get_cached(cache_key)
                if cached and ttl_logic(cached, source=source):
                    logger.info(f"✅ Кэш {cache_key}")
                    return cached
                logger.info(f"♻️ Кэш {cache_key} устарел или отсутствует")

            result = await func(request, *args, **kwargs)

            # Проверяем флаг fallback
            if isinstance(result, dict) and result.get("fallback"):
                logger.warning(f"☑️ Используем fallback {cache_key}")
                return fallback_data or {}

            if result is None:
                logger.warning(f"☑️ Используем fallback {cache_key}")
                return fallback_data or {}

            ttl_interval = ttl_logic(result, source=source, return_ttl=True)
            await set_cached(cache_key, result, ttl=ttl_interval)
            logger.info(f"🔁 Кэш {cache_key} обновлён, TTL = {ttl_interval}")

            return result

        return wrapper

    return decorator
