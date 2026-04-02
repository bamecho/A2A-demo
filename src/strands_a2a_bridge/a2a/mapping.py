"""A2A 类型与内部数据结构的映射工具."""

from __future__ import annotations

from a2a.types import Part, TextPart


def map_text_parts_to_content_blocks(parts: list[Part]) -> list[dict[str, str]]:
    """将 A2A TextPart 列表合并为单一的 content block（用于 Strands 处理）."""
    text_segments = [part.root.text for part in parts if isinstance(part.root, TextPart)]
    return [{"text": "\n".join(text_segments)}]
