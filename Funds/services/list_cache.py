import hashlib
import json
from django.core.cache import cache


def cached_list(namespace, version_key, query_params, compute):
    version = cache.get(version_key) or 1

    raw = json.dumps(dict(query_params), sort_keys=True)
    hashed = hashlib.md5(raw.encode()).hexdigest()

    key = f"{namespace}:v{version}:{hashed}"

    data = cache.get(key)
    if data is not None:
        return data

    data = compute()
    cache.set(key, data)
    return data


def bump_version(version_key):
    try:
        cache.incr(version_key)
    except Exception:
        v = cache.get(version_key) or 1
        cache.set(version_key, v + 1)
