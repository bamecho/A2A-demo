from a2a.types import MessageSendParams

from strands_a2a_bridge.a2a.mapping import map_text_parts_to_content_blocks


def _build_parts(*texts: str):
    return MessageSendParams.model_validate(
        {
            "message": {
                "kind": "message",
                "messageId": "msg-phase4-mapper",
                "role": "user",
                "parts": [{"kind": "text", "text": text} for text in texts],
            }
        }
    ).message.parts


def test_text_input_mapper_combines_text_parts_into_single_content_block():
    parts = _build_parts("alpha", "beta")

    assert map_text_parts_to_content_blocks(parts) == [{"text": "alpha\nbeta"}]


def test_text_input_mapper_keeps_single_text_part_as_single_block():
    parts = _build_parts("hello")

    assert map_text_parts_to_content_blocks(parts) == [{"text": "hello"}]
