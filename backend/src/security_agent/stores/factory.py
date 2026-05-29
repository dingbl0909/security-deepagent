from functools import lru_cache

from security_agent.stores.memory import InMemoryStores


@lru_cache
def get_in_memory_stores() -> InMemoryStores:
    return InMemoryStores()

