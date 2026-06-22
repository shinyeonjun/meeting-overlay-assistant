from server.app.services.retrieval.chunking.transcript_chunker import TranscriptTurnChunker


def test_transcript_turn_chunker_preserves_utterance_boundaries() -> None:
    chunker = TranscriptTurnChunker(target_chars=120, overlap_chars=40)
    markdown = "\n".join(
        [
            "# Note transcript",
            "",
            "## Transcript",
            "- [00:00-00:05] SPEAKER_00: 첫 번째 안건을 설명합니다.",
            "- [00:05-00:10] SPEAKER_01: 두 번째 의견을 말합니다.",
            "- [00:10-00:15] SPEAKER_00: 세 번째 결정을 정리합니다.",
            "- [00:15-00:20] SPEAKER_01: 네 번째 후속 작업을 말합니다.",
            "- [00:20-00:25] SPEAKER_00: 다섯 번째 리스크를 확인합니다.",
            "- [00:25-00:30] SPEAKER_01: 여섯 번째 담당자를 정합니다.",
            "- [00:30-00:35] SPEAKER_00: 일곱 번째 일정을 다시 확인합니다.",
            "- [00:35-00:40] SPEAKER_01: 여덟 번째 공유 범위를 확정합니다.",
            "- [00:40-00:45] SPEAKER_00: 아홉 번째 회의록 반영 기준을 말합니다.",
            "- [00:45-00:50] SPEAKER_01: 열 번째 다음 회의 준비 사항을 말합니다.",
        ]
    )

    chunks = chunker.chunk(markdown)

    assert len(chunks) >= 2
    assert all(chunk.heading == "Transcript" for chunk in chunks)
    assert all(chunk.text.startswith("- [") for chunk in chunks)
    assert all("\n" not in line or line.startswith("- [") for chunk in chunks for line in chunk.text.splitlines())
    assert chunks[0].metadata_json["chunk_strategy"] == "transcript_turn_boundary"
    assert chunks[0].metadata_json["section_role"] == "transcript"
    assert chunks[0].start_ms == 0
    assert chunks[0].end_ms is not None
    assert chunks[0].source_ref is not None


def test_transcript_turn_chunker_falls_back_for_plain_markdown() -> None:
    chunker = TranscriptTurnChunker(target_chars=120, overlap_chars=20)

    chunks = chunker.chunk("# Summary\n\nPlain report text without timestamped turns.")

    assert len(chunks) == 1
    assert chunks[0].metadata_json["chunk_strategy"] == "markdown_heading_fallback"
