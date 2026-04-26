"""노트 transcript corrector 동작을 검증한다."""
from __future__ import annotations

import json

from server.app.domain.models.utterance import Utterance
from server.app.services.reports.refinement import (
    NoteTranscriptCorrectionConfig,
    NoteTranscriptCorrector,
)


class _FlakyCompletionClient:
    def __init__(self) -> None:
        self.calls = 0
        self.keep_alive_values: list[str | None] = []

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema=None,
        keep_alive: str | None = None,
    ) -> str:
        del prompt, system_prompt, response_schema
        self.calls += 1
        self.keep_alive_values.append(keep_alive)
        if self.calls == 1:
            raise TimeoutError("timed out")
        return json.dumps(
            {
                "corrected_text": "Qwen 2.5로 바꿉니다.",
                "changed": True,
                "risk_flags": [],
            },
            ensure_ascii=False,
        )


def _build_utterance(*, seq_num: int, text: str) -> Utterance:
    return Utterance.create(
        session_id="session-test",
        seq_num=seq_num,
        start_ms=(seq_num - 1) * 1000,
        end_ms=seq_num * 1000,
        text=text,
        confidence=0.9,
        speaker_label="SPEAKER_00",
        transcript_source="post_processed",
        processing_job_id="job-test",
    )


class TestNoteTranscriptCorrector:
    """NoteTranscriptCorrector 동작을 검증한다."""
    def test_개별_발화_실패가_문서_전체를_중단시키지_않는다(self):
        client = _FlakyCompletionClient()
        corrector = NoteTranscriptCorrector(
            client,
            config=NoteTranscriptCorrectionConfig(
                model="gemma4:e4b",
                max_window=3,
                max_candidates=2,
                max_confidence_for_correction=1.0,
            ),
        )
        utterances = [
            _build_utterance(seq_num=1, text="첫 번째 원문입니다."),
            _build_utterance(seq_num=2, text="큐웬 투 점 오로 바꿉니다."),
        ]

        document = corrector.correct(
            session_id="session-test",
            source_version=1,
            utterances=utterances,
        )

        assert len(document.items) == 2
        assert document.items[0].corrected_text == "첫 번째 원문입니다."
        assert document.items[0].risk_flags == ["request_failed"]
        assert document.items[1].corrected_text == "Qwen 2.5로 바꿉니다."
        assert client.keep_alive_values == ["10m", "10m"]

    def test_안전한_발화는_llm_후보정에서_건너뛴다(self):
        client = _FlakyCompletionClient()
        corrector = NoteTranscriptCorrector(
            client,
            config=NoteTranscriptCorrectionConfig(
                model="gemma4:e4b",
                max_window=3,
                max_candidates=1,
                max_confidence_for_correction=0.5,
                short_utterance_max_chars=4,
            ),
        )
        utterances = [
            _build_utterance(seq_num=1, text="이건 충분히 길고 안정적인 발화입니다."),
            _build_utterance(seq_num=2, text="어어어"),
        ]

        document = corrector.correct(
            session_id="session-test",
            source_version=1,
            utterances=utterances,
        )

        assert len(document.items) == 2
        assert document.items[0].corrected_text == "이건 충분히 길고 안정적인 발화입니다."
        assert document.items[0].changed is False
        assert document.items[0].risk_flags == []
        assert client.calls == 1
