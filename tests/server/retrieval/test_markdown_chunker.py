from server.app.services.retrieval.chunking.markdown_chunker import MarkdownChunker


def test_markdown_chunker_splits_long_markdown_with_heading() -> None:
    chunker = MarkdownChunker(target_chars=80, overlap_chars=20)
    markdown = "# 결정 사항\n" + ("이 문장은 충분히 길어서 chunk 분리가 일어나야 합니다. " * 8)

    chunks = chunker.chunk(markdown)

    assert len(chunks) >= 2
    assert all(chunk.heading == "결정 사항" for chunk in chunks)
    assert all(chunk.text.strip() for chunk in chunks)
    assert all(chunk.metadata_json["section_role"] == "decision" for chunk in chunks)
    assert all(chunk.metadata_json["heading_path"] == ["결정 사항"] for chunk in chunks)


def test_markdown_chunker_marks_action_item_sections() -> None:
    chunker = MarkdownChunker(target_chars=200, overlap_chars=20)
    markdown = "# 회의록\n\n## 다음 할 일\n\n- 민수: QA 체크리스트를 갱신한다."

    chunks = chunker.chunk(markdown)

    action_chunks = [chunk for chunk in chunks if chunk.heading == "다음 할 일"]
    assert action_chunks
    assert action_chunks[0].metadata_json["section_role"] == "action_item"
    assert action_chunks[0].metadata_json["heading_path"] == ["회의록", "다음 할 일"]
