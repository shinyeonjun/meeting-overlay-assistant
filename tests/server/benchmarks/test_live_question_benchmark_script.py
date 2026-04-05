"""실시간 질문 벤치마크 스크립트 테스트."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from server.app.services.live_questions.models import (
    LiveQuestionOperation,
    LiveQuestionResult,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "server" / "scripts" / "audio" / "benchmark_live_questions.py"
SPEC = importlib.util.spec_from_file_location("benchmark_live_questions", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TestLiveQuestionBenchmarkScript:
    """질문 벤치마크 보조 함수 동작을 검증한다."""

    def test_default_dataset가_충분히_다양한_케이스를_포함한다(self):
        dataset = MODULE.load_dataset(
            TESTS_ROOT / "fixtures" / "support" / "live_questions_benchmark_v1.json",
        )
        case_ids = {item.case_id for item in dataset.cases}

        assert len(dataset.cases) >= 30
        assert "add_two_questions_same_turn" in case_ids
        assert "close_and_add_new_question" in case_ids
        assert "no_question_question_word_in_statement" in case_ids
        assert "keep_open_if_answer_is_todo" in case_ids

    def test_load_dataset가_json_케이스를_불러온다(self, tmp_path):
        dataset_path = tmp_path / "dataset.json"
        dataset_path.write_text(
            json.dumps(
                {
                    "name": "sample",
                    "description": "샘플 데이터셋",
                    "cases": [
                        {
                            "id": "case-1",
                            "description": "질문 add 케이스",
                            "utterances": [
                                {
                                    "id": "u-1",
                                    "text": "배포 일정은 언제 확정되나요?",
                                    "speaker_label": "SPEAKER_00",
                                    "timestamp_ms": 1000,
                                    "confidence": 0.92,
                                }
                            ],
                            "open_questions": [],
                            "expected_operations": [
                                {
                                    "op": "add",
                                    "accepted_summaries": ["배포 일정 확정 시점 질문"],
                                }
                            ],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        dataset = MODULE.load_dataset(dataset_path)

        assert dataset.name == "sample"
        assert dataset.description == "샘플 데이터셋"
        assert len(dataset.cases) == 1
        assert dataset.cases[0].case_id == "case-1"
        assert dataset.cases[0].utterances[0].text == "배포 일정은 언제 확정되나요?"

    def test_evaluate_case가_add_exact_match를_집계한다(self):
        dataset = MODULE.load_dataset(
            TESTS_ROOT / "fixtures" / "support" / "live_questions_benchmark_v1.json",
            limit=1,
        )
        case = dataset.cases[0]
        result = LiveQuestionResult(
            session_id=case.to_request().session_id,
            window_id=case.case_id,
            operations=(
                LiveQuestionOperation(
                    op="add",
                    summary=case.expected_operations[0].accepted_summaries[0],
                    confidence=0.91,
                    evidence_utterance_ids=("u-1",),
                ),
            ),
        )

        evaluation = MODULE.evaluate_case(
            case=case,
            result=result,
            latency_ms=123.4,
        )

        assert evaluation.exact_match is True
        assert evaluation.add_true_positive == 1
        assert evaluation.add_false_positive == 0
        assert evaluation.add_false_negative == 0
        assert evaluation.close_true_positive == 0

    def test_evaluate_case가_close_exact_match를_집계한다(self):
        dataset = MODULE.load_dataset(
            TESTS_ROOT / "fixtures" / "support" / "live_questions_benchmark_v1.json",
        )
        case = next(item for item in dataset.cases if item.case_id == "close_answered_question")
        result = LiveQuestionResult(
            session_id=case.to_request().session_id,
            window_id=case.case_id,
            operations=(
                LiveQuestionOperation(
                    op="close",
                    target_question_id="q-release-time",
                    reason="answered",
                ),
            ),
        )

        evaluation = MODULE.evaluate_case(
            case=case,
            result=result,
            latency_ms=88.0,
        )

        assert evaluation.exact_match is True
        assert evaluation.close_true_positive == 1
        assert evaluation.close_false_positive == 0
        assert evaluation.close_false_negative == 0

    def test_run_benchmark가_fake_client_결과를_모아준다(self, monkeypatch):
        dataset = MODULE.load_dataset(
            TESTS_ROOT / "fixtures" / "support" / "live_questions_benchmark_v1.json",
            limit=2,
        )

        class FakeClient:
            def __init__(self, **_kwargs):
                self.calls = 0

            def analyze(self, request):
                self.calls += 1
                if request.window_id == "add_release_schedule_question":
                    return LiveQuestionResult(
                        session_id=request.session_id,
                        window_id=request.window_id,
                        operations=(
                            LiveQuestionOperation(
                                op="add",
                                summary="이번 배포 일정 확정 시점 질문",
                                confidence=0.87,
                                evidence_utterance_ids=("u-1",),
                            ),
                        ),
                    )
                if request.window_id == "add_budget_question_with_context":
                    return LiveQuestionResult(
                        session_id=request.session_id,
                        window_id=request.window_id,
                        operations=(
                            LiveQuestionOperation(
                                op="add",
                                summary="비용 승인 주체 질문",
                                confidence=0.83,
                                evidence_utterance_ids=("u-3",),
                            ),
                        ),
                    )
                return LiveQuestionResult(
                    session_id=request.session_id,
                    window_id=request.window_id,
                    operations=(),
                )

        monkeypatch.setattr(MODULE, "LiveQuestionLLMClient", FakeClient)

        evaluations = MODULE.run_benchmark(
            dataset=dataset,
            backend="fake",
            model="fake-model",
            base_url="http://127.0.0.1:9999/v1",
            api_key=None,
            timeout_seconds=1.0,
        )
        summary = MODULE._summarize(dataset, evaluations)

        assert len(evaluations) == 2
        assert summary["dataset"]["case_count"] == 2
        assert summary["metrics"]["failure_count"] == 0
        assert summary["metrics"]["error_count"] == 0
