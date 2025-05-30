# service/cache.py
import logging
from datetime import datetime, timedelta, timezone

from fastapi_cache import FastAPICache

from service.configs import CACHE_TTL


def get_backend():
    backend = FastAPICache.get_backend()
    if not backend:
        raise RuntimeError("Кэш не инициализирован")
    return backend


async def get_cached(key: str):
    backend = get_backend()
    return await backend.get(key)


async def set_cached(key: str, value: dict, ttl: int):
    backend = get_backend()
    await backend.set(key, value, expire=ttl)


def ttl_logic(
    data: dict,
    source: str = "auto",
    return_ttl: bool = False,
) -> int | bool:
    """
    Для любого source возвращает True если кэш валиден (до конца текущего интервала),
    либо TTL до конца интервала (интервал задаётся через CACHE_TTL в секундах, если return_ttl=True).
    """
    try:
        # Определяем ключ для CACHE_TTL
        if source == "auto":
            if "current_weather" in data:
                source = "weather"
            elif isinstance(data, dict) and all(
                k in data for k in ("id", "url", "width", "height")
            ):
                source = "cat"
            else:
                source = None

        # Определяем имя ключа для CACHE_TTL
        cache_key = f"{source}_cache" if source else None
        interval_sec = CACHE_TTL.get(cache_key, 60)
        now_utc = datetime.now(timezone.utc)
        # Вычисляем начало и конец текущего интервала
        interval_start = now_utc - timedelta(seconds=now_utc.timestamp() % interval_sec)
        interval_end = interval_start + timedelta(seconds=interval_sec)

        if return_ttl:
            # TTL до конца текущего интервала
            ttl = int((interval_end - now_utc).total_seconds())
            # Если вдруг ttl=0, то возвращаем полный интервал, чтобы не было нулевого TTL
            return ttl if ttl > 0 else interval_sec

        # Кэш валиден, если текущее время меньше конца интервала
        return now_utc < interval_end

    except Exception as e:
        logging.warning(f"TTL error for {source}: {e}")
        if return_ttl:
            return 60
        return False
