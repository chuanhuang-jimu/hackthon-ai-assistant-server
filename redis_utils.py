import requests
import json
import httpx


def query_redis(method: str, key: str) -> dict:
    url = f"http://localhost:7379/{method}/{key}"
    data = {}
    try:
        response = requests.get(url)
        # A 404 from webdis means the key doesn't exist, which is not an error in our case.
        if response.status_code == 404:
            return {}
        response.raise_for_status()  # Raise an exception for other bad statuses (500, 403, etc.)

        response_json = response.json()
        raw_json_string = response_json.get(method)

        if raw_json_string and isinstance(raw_json_string, str):
            try:
                data = json.loads(raw_json_string)
            except json.JSONDecodeError:
                data = raw_json_string
        # If the key exists but the value is not a string (e.g. Redis list),
        # webdis might return it directly as a JSON array.
        elif raw_json_string and isinstance(raw_json_string, list):
             data = raw_json_string

    except requests.exceptions.RequestException as e:
        print(f"Error querying redis key '{key}': {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from redis for key '{key}': {e}. Response was: {response.text}")
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred in query_redis for key '{key}': {e}")

    return data


async def async_query_redis(method: str, key: str) -> dict:
    url = f"http://localhost:7379/{method}/{key}"
    data = {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 404:
                return {}
            response.raise_for_status()

            response_json = response.json()
            raw_json_string = response_json.get(method)

            if raw_json_string and isinstance(raw_json_string, str):
                try:
                    data = json.loads(raw_json_string)
                except json.JSONDecodeError:
                    data = raw_json_string
            elif raw_json_string and isinstance(raw_json_string, list):
                 data = raw_json_string

    except httpx.HTTPError as e:
        print(f"Error querying redis key '{key}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred in async_query_redis for key '{key}': {e}")

    return data


def set_redis(key: str, value, expiry_seconds: int = None) -> None:
    if not isinstance(value, str):
        value_str = json.dumps(value)
    else:
        value_str = value

    command = "SET"
    url = f"http://localhost:7379/{command}/{key}"
    
    if expiry_seconds:
        # For SETEX, webdis seems to use path parameters for seconds
        url = f"http://localhost:7379/SETEX/{key}/{expiry_seconds}"

    try:
        # Use the data parameter to send the value in the request body
        response = requests.put(url, data=value_str)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error setting redis key '{key}': {e}")


async def async_set_redis(key: str, value, expiry_seconds: int = None) -> None:
    if not isinstance(value, str):
        value_str = json.dumps(value)
    else:
        value_str = value

    command = "SET"
    url = f"http://localhost:7379/{command}/{key}"
    
    if expiry_seconds:
        url = f"http://localhost:7379/SETEX/{key}/{expiry_seconds}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(url, content=value_str)
            response.raise_for_status()
    except httpx.HTTPError as e:
        print(f"Error setting redis key '{key}': {e}")