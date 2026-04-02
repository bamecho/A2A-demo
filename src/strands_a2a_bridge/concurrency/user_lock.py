from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio


class UserBusyError(RuntimeError):
    pass


class UserRequestGuard:
    def __init__(self) -> None:
        self._state_lock = anyio.Lock()
        self._active_user_ids: set[str] = set()

    @asynccontextmanager
    async def claim(self, user_id: str) -> AsyncIterator[None]:
        async with self._state_lock:
            if user_id in self._active_user_ids:
                raise UserBusyError("Another request is already active for this user")
            self._active_user_ids.add(user_id)

        try:
            yield
        finally:
            async with self._state_lock:
                self._active_user_ids.discard(user_id)
