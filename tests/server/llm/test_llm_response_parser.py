"""공통 영역의 test llm response parser 동작을 검증한다."""
from server.app.services.analysis.llm.extraction.llm_response_parser import (
    LLMAnalysisResponseParser,
)


class TestLLMAnalysisResponseParser:
    """응답 파서 동작을 검증한다."""

    def test_정상_json은_이벤트_후보_목록으로_파싱된다(self):
        parser = LLMAnalysisResponseParser()

        result = parser.parse(
            '{"candidates":[{"event_type":"decision","title":"이번 배포에서는 이 수정은 제외합시다.","state":"confirmed","body":null}]}'
        )

        assert len(result.candidates) == 1
        assert result.candidates[0].event_type == "decision"
        assert result.candidates[0].title == "이번 배포에서는 이 수정은 제외합시다."

    def test_루트가_리스트여도_이벤트_후보_목록으로_파싱된다(self):
        parser = LLMAnalysisResponseParser()

        result = parser.parse(
            '[{"event_type":"question","title":"이 기능이 동작하나요?","state":"open","body":null}]'
        )

        assert len(result.candidates) == 1
        assert result.candidates[0].event_type == "question"

    def test_topic_타입도_정상_후보로_받아들인다(self):
        parser = LLMAnalysisResponseParser()

        result = parser.parse(
            '{"candidates":[{"event_type":"topic","title":"이번 회의 주제","state":"active","body":"현재 논의 주제"}]}'
        )

        assert len(result.candidates) == 1
        assert result.candidates[0].event_type == "topic"
        assert result.candidates[0].state == "active"

    def test_잘못된_json이면_빈_결과를_반환한다(self):
        parser = LLMAnalysisResponseParser()

        result = parser.parse("not-json")

        assert result.candidates == []
