from __future__ import annotations

from a2a.types import Part, TextPart


def map_text_parts_to_content_blocks(parts: list[Part]) -> list[dict[str, str]]:
    text_segments = [part.root.text for part in parts if isinstance(part.root, TextPart)]
    return [{"text": "\n".join(text_segments)}]
