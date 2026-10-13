"""회의 기록 화자 이름 API 테스트."""

from dataclasses import replace

from server.app.api.http.wiring.persistence import get_session_repository, get_utterance_repository
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import PostProcessingStatus


def _create_session_with_speakers(client, labels):
    response = client.post(
        "/api/v1/sessions",
        json={"title": "화자 이름 테스트", "mode": "meeting", "source": "system_audio"},
    )
    session_id = response.json()["id"]
    repository = get_utterance_repository()
    for index, label in enumerate(labels, start=1):
        repository.save(
            Utterance.create(
                session_id=session_id,
                seq_num=index,
                start_ms=index * 1000,
                end_ms=index * 1000 + 800,
                text=f"발화 {index}",
                confidence=0.9,
                input_source="system_audio",
                speaker_label=label,
                transcript_source="post_processed",
            )
        )
    return session_id


class TestSessionSpeakersApi:
    def test_화자_목록은_처음_말한_순서대로_기본_이름을_준다(self, client):
        session_id = _create_session_with_speakers(client, ["SPEAKER_01", "SPEAKER_00", "SPEAKER_01"])

        response = client.get(f"/api/v1/sessions/{session_id}/speakers")

        assert response.status_code == 200
        assert response.json()["max_name_length"] == 40
        items = response.json()["items"]
        assert [(item["speaker_label"], item["display_name"], item["utterance_count"]) for item in items] == [
            ("SPEAKER_01", "화자 1", 2),
            ("SPEAKER_00", "화자 2", 1),
        ]
        assert all(item["custom_name"] is None for item in items)

    def test_이름을_붙이면_같은_화자의_모든_발화에_반영된다(self, client):
        session_id = _create_session_with_speakers(client, ["SPEAKER_00", "SPEAKER_01", "SPEAKER_00"])

        response = client.put(
            f"/api/v1/sessions/{session_id}/speakers",
            json={"speaker_label": "SPEAKER_00", "display_name": "  김민수 "},
        )

        assert response.status_code == 200
        first = response.json()["items"][0]
        assert first["display_name"] == "김민수"
        assert first["custom_name"] == "김민수"
        assert first["default_name"] == "화자 1"

        transcript = client.get(f"/api/v1/sessions/{session_id}/transcript").json()
        assert [item["speaker_name"] for item in transcript["items"]] == ["김민수", "화자 2", "김민수"]

    def test_빈_이름으로_바꾸면_기본_이름으로_돌아간다(self, client):
        session_id = _create_session_with_speakers(client, ["SPEAKER_00"])
        client.put(
            f"/api/v1/sessions/{session_id}/speakers",
            json={"speaker_label": "SPEAKER_00", "display_name": "김민수"},
        )

        response = client.put(
            f"/api/v1/sessions/{session_id}/speakers",
            json={"speaker_label": "SPEAKER_00", "display_name": "   "},
        )

        assert response.status_code == 200
        assert response.json()["items"][0]["display_name"] == "화자 1"
        assert response.json()["items"][0]["custom_name"] is None

    def test_회의에_없는_화자는_404다(self, client):
        session_id = _create_session_with_speakers(client, ["SPEAKER_00"])

        response = client.put(
            f"/api/v1/sessions/{session_id}/speakers",
            json={"speaker_label": "SPEAKER_09", "display_name": "김민수"},
        )

        assert response.status_code == 404

    def test_너무_긴_이름은_400이다(self, client):
        session_id = _create_session_with_speakers(client, ["SPEAKER_00"])

        response = client.put(
            f"/api/v1/sessions/{session_id}/speakers",
            json={"speaker_label": "SPEAKER_00", "display_name": "가" * 41},
        )

        assert response.status_code == 400

    def test_화자_분리를_안_한_회의는_참석자_한_명으로_보이고_이름을_붙일_수_있다(self, client):
        session_id = _create_session_with_speakers(client, [None, None])

        speakers = client.get(f"/api/v1/sessions/{session_id}/speakers").json()["items"]
        assert [(item["speaker_label"], item["display_name"]) for item in speakers] == [
            ("speaker-unknown", "참석자"),
        ]

        client.put(
            f"/api/v1/sessions/{session_id}/speakers",
            json={"speaker_label": "speaker-unknown", "display_name": "김민수"},
        )
        transcript = client.get(f"/api/v1/sessions/{session_id}/transcript").json()
        assert [item["speaker_name"] for item in transcript["items"]] == ["김민수", "김민수"]

    def test_후처리를_다시_돌려_transcript_버전이_바뀌면_옛_이름은_쓰지_않는다(self, client):
        session_id = _create_session_with_speakers(client, ["SPEAKER_00"])
        client.put(
            f"/api/v1/sessions/{session_id}/speakers",
            json={"speaker_label": "SPEAKER_00", "display_name": "김민수"},
        )

        session_repository = get_session_repository()
        session = session_repository.get_by_id(session_id)
        assert session is not None
        session_repository.save(
            replace(
                session,
                post_processing=replace(
                    session.post_processing,
                    canonical_transcript_version=session.canonical_transcript_version + 1,
                ),
            )
        )

        speakers = client.get(f"/api/v1/sessions/{session_id}/speakers").json()["items"]
        assert speakers[0]["display_name"] == "화자 1"
        assert speakers[0]["custom_name"] is None

    def test_회의_정리_중에는_이름을_바꿀_수_없다(self, client):
        session_id = _create_session_with_speakers(client, ["SPEAKER_00"])
        session_repository = get_session_repository()
        session = session_repository.get_by_id(session_id)
        assert session is not None
        session_repository.save(
            replace(
                session,
                post_processing=replace(
                    session.post_processing,
                    status=PostProcessingStatus.PROCESSING,
                ),
            )
        )

        response = client.put(
            f"/api/v1/sessions/{session_id}/speakers",
            json={"speaker_label": "SPEAKER_00", "display_name": "김민수"},
        )

        assert response.status_code == 409
