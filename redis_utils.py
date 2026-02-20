import redis
import redis.asyncio as async_redis
import json
import os

# Configure Redis connection - defaulting to localhost:6379
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Initialize clients with decode_responses=True to handle strings automatically
sync_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
async_client = async_redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


def query_redis(method: str, key: str) -> any:
    """
    Query redis using the specified method (e.g., 'GET').
    """
    try:
        method_lower = method.lower()
        if method_lower == 'get':
            raw_data = sync_client.get(key)
        else:
            # Fallback for other Redis commands if needed
            func = getattr(sync_client, method_lower)
            raw_data = func(key)

        if raw_data is None:
            return None

        if isinstance(raw_data, str):
            try:
                # Attempt to parse JSON if it looks like it
                if (raw_data.startswith('{') and raw_data.endswith('}')) or \
                   (raw_data.startswith('[') and raw_data.endswith(']')):
                    return json.loads(raw_data)
                return raw_data
            except (json.JSONDecodeError, TypeError):
                return raw_data
        return raw_data

    except Exception as e:
        print(f"Error querying redis key '{key}' with method '{method}': {e}")
        return {}


async def async_query_redis(method: str, key: str) -> any:
    """
    Asynchronously query redis using the specified method.
    """
    try:
        method_lower = method.lower()
        if method_lower == 'get':
            raw_data = await async_client.get(key)
        else:
            func = getattr(async_client, method_lower)
            raw_data = await func(key)

        if raw_data is None:
            return None

        if isinstance(raw_data, str):
            try:
                if (raw_data.startswith('{') and raw_data.endswith('}')) or \
                   (raw_data.startswith('[') and raw_data.endswith(']')):
                    return json.loads(raw_data)
                return raw_data
            except (json.JSONDecodeError, TypeError):
                return raw_data
        return raw_data

    except Exception as e:
        print(f"An unexpected error occurred in async_query_redis for key '{key}': {e}")
        return {}


def set_redis(key: str, value, expiry_seconds: int = None) -> None:
    """
    Set a redis key with an optional expiry.
    Automatically serializes non-string values to JSON.
    """
    try:
        if not isinstance(value, (str, bytes, int, float)):
            value_str = json.dumps(value)
        else:
            value_str = value

        sync_client.set(key, value_str, ex=expiry_seconds)
    except Exception as e:
        print(f"Error setting redis key '{key}': {e}")


async def async_set_redis(key: str, value, expiry_seconds: int = None) -> None:
    """
    Asynchronously set a redis key with an optional expiry.
    """
    try:
        if not isinstance(value, (str, bytes, int, float)):
            value_str = json.dumps(value)
        else:
            value_str = value

        await async_client.set(key, value_str, ex=expiry_seconds)
    except Exception as e:
        print(f"Error setting redis key '{key}': {e}")
