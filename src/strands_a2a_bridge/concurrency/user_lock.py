"""用户级请求互斥锁：防止同一用户的并发请求."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio


class UserBusyError(RuntimeError):
    """用户已有活跃请求时抛出的异常."""
    pass


class UserRequestGuard:
    """管理用户请求状态，确保同一时刻每个用户只有一个活跃请求.
    
    使用 async 上下文管理器实现请求声明和自动清理.
    """

    def __init__(self) -> None:
        # 保护 _active_user_ids 集合的锁
        self._state_lock = anyio.Lock()
        # 当前活跃的用户 ID 集合
        self._active_user_ids: set[str] = set()

    @asynccontextmanager
    async def claim(self, user_id: str) -> AsyncIterator[None]:
        """声明用户请求独占权，退出上下文时自动释放.
        
        Raises:
            UserBusyError: 该用户已有其他活跃请求
        """
        async with self._state_lock:
            if user_id in self._active_user_ids:
                raise UserBusyError("Another request is already active for this user")
            self._active_user_ids.add(user_id)

        try:
            yield
        finally:
            async with self._state_lock:
                self._active_user_ids.discard(user_id)
