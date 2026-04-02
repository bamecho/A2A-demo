from strands_a2a_bridge.manager.fake import FakeAgentProvider


def test_fake_manager_reuses_agent_for_same_user() -> None:
    provider = FakeAgentProvider()

    first = provider.get_or_create_agent("user-1")
    second = provider.get_or_create_agent("user-1")

    assert first is second
    assert first.agent_id
    assert second.agent_id == first.agent_id


def test_fake_manager_isolates_agents_for_different_users() -> None:
    provider = FakeAgentProvider()

    first = provider.get_or_create_agent("user-1")
    second = provider.get_or_create_agent("user-2")

    assert first is not second
    assert first.agent_id
    assert second.agent_id
    assert first.agent_id != second.agent_id
