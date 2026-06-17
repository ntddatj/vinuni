import asyncio

_registry: dict[str, asyncio.Queue[str | None]] = {}
_owners: dict[str, str] = {}


def create_run(run_id: str, user_id: str) -> asyncio.Queue[str | None]:
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    _registry[run_id] = queue
    _owners[run_id] = user_id
    return queue


def get_run_queue(run_id: str) -> asyncio.Queue[str | None] | None:
    return _registry.get(run_id)


def get_run_owner(run_id: str) -> str | None:
    return _owners.get(run_id)


def delete_run(run_id: str) -> None:
    _registry.pop(run_id, None)
    _owners.pop(run_id, None)
