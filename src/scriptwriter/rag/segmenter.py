from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    segment_type: str
    order_index: int
    heading: str | None
    text: str


@dataclass(frozen=True)
class Chunk:
    segment_type: str
    segment_index: int
    chunk_index: int
    text: str


_SCRIPT_SCENE_RE = re.compile(r"(?m)^\s*(INT\.|EXT\.)[^\n]*$")
_NOVEL_CHAPTER_RE = re.compile(
    r"(?m)^\s*((CHAPTER|Chapter)\s+\w+|第[一二三四五六七八九十百千0-9]+章)\s*$"
)


def _split_by_heading(
    content: str,
    heading_pattern: re.Pattern[str],
    segment_type: str,
) -> list[Segment]:
    matches = list(heading_pattern.finditer(content))
    if not matches:
        return []

    segments: list[Segment] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        block = content[start:end].strip()
        if not block:
            continue
        heading = match.group(0).strip()
        segments.append(
            Segment(
                segment_type=segment_type,
                order_index=len(segments),
                heading=heading,
                text=block,
            )
        )
    return segments


def _fallback_paragraph_segments(content: str) -> list[Segment]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    if not paragraphs:
        paragraphs = [content.strip()] if content.strip() else []
    return [
        Segment(segment_type="paragraph", order_index=idx, heading=None, text=paragraph)
        for idx, paragraph in enumerate(paragraphs)
    ]


def segment_content(content: str, doc_type: str) -> list[Segment]:
    body = content.strip()
    if not body:
        return []

    normalized_type = doc_type.lower().strip()
    if normalized_type == "script":
        segments = _split_by_heading(body, _SCRIPT_SCENE_RE, "scene")
        return segments if segments else _fallback_paragraph_segments(body)
    if normalized_type == "novel":
        segments = _split_by_heading(body, _NOVEL_CHAPTER_RE, "chapter")
        return segments if segments else _fallback_paragraph_segments(body)
    return _fallback_paragraph_segments(body)


def chunk_segments(
    segments: list[Segment],
    *,
    max_chars: int = 800,
    overlap: int = 120,
) -> list[Chunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= max_chars:
        raise ValueError("overlap must be < max_chars")

    chunks: list[Chunk] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        if len(text) <= max_chars:
            chunks.append(
                Chunk(
                    segment_type=segment.segment_type,
                    segment_index=segment.order_index,
                    chunk_index=0,
                    text=text,
                )
            )
            continue

        start = 0
        chunk_idx = 0
        stride = max_chars - overlap
        while start < len(text):
            piece = text[start : start + max_chars].strip()
            if piece:
                chunks.append(
                    Chunk(
                        segment_type=segment.segment_type,
                        segment_index=segment.order_index,
                        chunk_index=chunk_idx,
                        text=piece,
                    )
                )
                chunk_idx += 1
            start += stride
    return chunks
