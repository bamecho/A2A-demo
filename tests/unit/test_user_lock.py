import pytest

from strands_a2a_bridge.concurrency.user_lock import UserBusyError, UserRequestGuard


@pytest.mark.anyio
async def test_user_lock_rejects_second_active_request_for_same_user() -> None:
    guard = UserRequestGuard()

    async with guard.claim("user-1"):
        with pytest.raises(UserBusyError):
            async with guard.claim("user-1"):
                pass


@pytest.mark.anyio
async def test_user_lock_allows_different_users_to_be_active_together() -> None:
    guard = UserRequestGuard()

    async with guard.claim("user-1"):
        async with guard.claim("user-2"):
            pass


@pytest.mark.anyio
async def test_user_lock_releases_user_after_request_finishes() -> None:
    guard = UserRequestGuard()

    async with guard.claim("user-1"):
        pass

    async with guard.claim("user-1"):
        pass
