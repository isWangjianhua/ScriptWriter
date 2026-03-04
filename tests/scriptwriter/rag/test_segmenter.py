from scriptwriter.rag.segmenter import chunk_segments, segment_content


def test_segment_script_by_scene_heading():
    content = """
INT. OFFICE - DAY
John enters.

EXT. STREET - NIGHT
Cars rush by.
""".strip()
    segments = segment_content(content, "script")
    assert len(segments) == 2
    assert segments[0].segment_type == "scene"
    assert "INT. OFFICE" in segments[0].heading


def test_segment_plain_text_fallback():
    content = "Paragraph one.\n\nParagraph two."
    segments = segment_content(content, "text")
    assert len(segments) == 2
    assert all(s.segment_type == "paragraph" for s in segments)


def test_chunking_generates_multiple_chunks():
    text = "A" * 1700
    segments = segment_content(text, "text")
    chunks = chunk_segments(segments, max_chars=800, overlap=100)
    assert len(chunks) >= 2
