"""검색 증강 영역의 test markdown chunker 동작을 검증한다."""
from server.app.services.retrieval.chunking.markdown_chunker import MarkdownChunker


def test_markdown_chunker_splits_long_markdown_with_heading() -> None:
    """markdown chunker splits long markdown with heading 동작을 검증한다."""
    chunker = MarkdownChunker(target_chars=80, overlap_chars=20)
    markdown = "# 결정 사항\n" + ("이 문장은 충분히 길어서 chunk 분리가 일어나야 합니다. " * 8)

    chunks = chunker.chunk(markdown)

    assert len(chunks) >= 2
    assert all(chunk.heading == "결정 사항" for chunk in chunks)
    assert all(chunk.text.strip() for chunk in chunks)
