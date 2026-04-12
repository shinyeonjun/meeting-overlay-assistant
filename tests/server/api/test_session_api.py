"""세션 API 테스트"""


from server.app.api.http.wiring.persistence import get_utterance_repository
from server.app.api.http.wiring.artifact_storage import get_local_artifact_store
from server.app.domain.models.utterance import Utterance
from server.app.services.audio.io.session_recording import build_session_recording_artifact
from server.app.services.reports.refinement import (
    TranscriptCorrectionDocument,
    TranscriptCorrectionItem,
    TranscriptCorrectionStore,
)

import shutil
import wave


class TestSessionApi:
    """세션 생성과 종료 API를 검증한다."""

    def test_세션_생성_api를_호출하면_draft_세션을_반환한다(self, client):
        response = client.post(
            "/api/v1/sessions",
            json={
                "title": "테스트 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "테스트 회의"
        assert payload["status"] == "draft"
        assert payload["id"].startswith("session-")
        assert payload["primary_input_source"] == "system_audio"

    def test_draft_세션을_시작하면_running_상태가_된다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "시작 테스트 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]

        response = client.post(f"/api/v1/sessions/{session_id}/start")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "running"
        assert payload["ended_at"] is None

    def test_세션_상세_api를_호출하면_세션을_반환한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "상세 조회 테스트 회의",
                "mode": "meeting",
                "source": "system_audio",
                "participants": ["김영희"],
            },
        )
        session_id = create_response.json()["id"]

        response = client.get(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == session_id
        assert payload["title"] == "상세 조회 테스트 회의"
        assert payload["primary_input_source"] == "system_audio"
        assert payload["participants"] == ["김영희"]

    def test_세션_종료_api를_호출하면_ended_상태만_반환한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "종료 테스트 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")

        response = client.post(f"/api/v1/sessions/{session_id}/end")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ended"
        assert payload["ended_at"] is not None
        assert payload["post_processing_status"] == "queued"
        assert payload["recording_artifact_id"] is None

        reports_response = client.get(f"/api/v1/reports/{session_id}")
        reports_payload = reports_response.json()
        assert reports_response.status_code == 200
        assert reports_payload["items"] == []

    def test_세션_종료후_processing_api로_후처리_대기상태를_조회할_수_있다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "후처리 상태 조회 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")

        end_response = client.post(f"/api/v1/sessions/{session_id}/end")
        processing_response = client.get(f"/api/v1/sessions/{session_id}/processing")

        assert end_response.status_code == 200
        assert processing_response.status_code == 200
        payload = processing_response.json()
        assert payload["session_id"] == session_id
        assert payload["status"] == "queued"
        assert payload["latest_job_id"] is not None
        assert payload["latest_job_status"] == "pending"
        assert payload["canonical_transcript_version"] == 0
        assert payload["canonical_events_version"] == 0

    def test_세션_transcript_api가_canonical_utterances를_반환한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "transcript 조회 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_payload = create_response.json()
        session_id = session_payload["id"]

        utterance_repository = get_utterance_repository()
        utterance_repository.save(
            Utterance.create(
                session_id=session_id,
                seq_num=1,
                start_ms=3000,
                end_ms=8700,
                text="안건부터 빠르게 정리하겠습니다.",
                confidence=0.94,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
                processing_job_id="post-job-test",
            )
        )
        utterance_repository.save(
            Utterance.create(
                session_id=session_id,
                seq_num=2,
                start_ms=9100,
                end_ms=15400,
                text="다음 주까지 초안을 공유드릴게요.",
                confidence=0.91,
                input_source="system_audio",
                speaker_label="SPEAKER_01",
                transcript_source="post_processed",
                processing_job_id="post-job-test",
            )
        )

        response = client.get(f"/api/v1/sessions/{session_id}/transcript")

        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == session_id
        assert payload["status"] == session_payload["post_processing_status"]
        assert payload["canonical_transcript_version"] == 0
        assert payload["items"] == [
            {
                "id": payload["items"][0]["id"],
                "seq_num": 1,
                "speaker_label": "SPEAKER_00",
                "start_ms": 3000,
                "end_ms": 8700,
                "text": "안건부터 빠르게 정리하겠습니다.",
                "raw_text": "안건부터 빠르게 정리하겠습니다.",
                "is_corrected": False,
                "confidence": 0.94,
                "input_source": "system_audio",
                "transcript_source": "post_processed",
                "processing_job_id": "post-job-test",
            },
            {
                "id": payload["items"][1]["id"],
                "seq_num": 2,
                "speaker_label": "SPEAKER_01",
                "start_ms": 9100,
                "end_ms": 15400,
                "text": "다음 주까지 초안을 공유드릴게요.",
                "raw_text": "다음 주까지 초안을 공유드릴게요.",
                "is_corrected": False,
                "confidence": 0.91,
                "input_source": "system_audio",
                "transcript_source": "post_processed",
                "processing_job_id": "post-job-test",
            },
        ]

    def test_세션_transcript_api가_보정본이_있으면_우선_반환한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "transcript 보정 조회 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_payload = create_response.json()
        session_id = session_payload["id"]

        utterance_repository = get_utterance_repository()
        utterance = Utterance.create(
            session_id=session_id,
            seq_num=1,
            start_ms=1000,
            end_ms=4200,
            text="큐웬 투 점 오는 괜찮습니다.",
            confidence=0.89,
            input_source="system_audio",
            speaker_label="SPEAKER_00",
            transcript_source="post_processed",
            processing_job_id="post-job-test",
        )
        utterance_repository.save(utterance)

        correction_store = TranscriptCorrectionStore(get_local_artifact_store())
        correction_store.save(
            TranscriptCorrectionDocument(
                session_id=session_id,
                source_version=0,
                model="gemma4:e4b",
                items=[
                    TranscriptCorrectionItem(
                        utterance_id=utterance.id,
                        raw_text=utterance.text,
                        corrected_text="Qwen 2.5는 괜찮습니다.",
                        changed=True,
                        risk_flags=["latin_product_name"],
                    )
                ],
            )
        )

        try:
            response = client.get(f"/api/v1/sessions/{session_id}/transcript")
            assert response.status_code == 200
            payload = response.json()
            assert payload["items"][0]["text"] == "Qwen 2.5는 괜찮습니다."
            assert payload["items"][0]["raw_text"] == "큐웬 투 점 오는 괜찮습니다."
            assert payload["items"][0]["is_corrected"] is True
        finally:
            correction_store.delete(session_id)

    def test_세션_recording_api가_inline_wav를_반환한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "recording 조회 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        artifact = build_session_recording_artifact(session_id, "system_audio")
        artifact.file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with wave.open(str(artifact.file_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(b"\x00\x00" * 1600)

            response = client.get(f"/api/v1/sessions/{session_id}/recording")
            detail_response = client.get(f"/api/v1/sessions/{session_id}")
            overview_response = client.get(f"/api/v1/sessions/{session_id}/overview")

            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/wav"
            assert "inline" in response.headers["content-disposition"]
            assert response.content[:4] == b"RIFF"
            assert detail_response.status_code == 200
            assert detail_response.json()["recording_available"] is True
            assert overview_response.status_code == 200
            assert overview_response.json()["session"]["recording_available"] is True
        finally:
            shutil.rmtree(artifact.file_path.parent, ignore_errors=True)

    def test_세션_recording_api는_파일이_없으면_404다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "recording 없음 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]

        response = client.get(f"/api/v1/sessions/{session_id}/recording")

        assert response.status_code == 404
        assert response.json()["detail"] == "세션 녹음 파일을 찾을 수 없습니다."

    def test_세션_이름을_patch로_변경할_수_있다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "이름 변경 전",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/sessions/{session_id}",
            json={"title": "이름 변경 후"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "이름 변경 후"

    def test_종료된_세션은_delete로_삭제할_수_있고_녹음_artifact도_정리된다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "삭제 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        artifact = build_session_recording_artifact(session_id, "system_audio")
        artifact.file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with wave.open(str(artifact.file_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(b"\x00\x00" * 800)

            delete_response = client.delete(f"/api/v1/sessions/{session_id}")

            assert delete_response.status_code == 204
            assert client.get(f"/api/v1/sessions/{session_id}").status_code == 404
            assert not artifact.file_path.parent.exists()
        finally:
            shutil.rmtree(artifact.file_path.parent, ignore_errors=True)

    def test_실제로_진행중인_세션은_delete할_수_없다(self, client, monkeypatch):
        from server.app.api.http.dependencies import get_live_stream_service

        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "삭제 제한 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")
        monkeypatch.setattr(
            get_live_stream_service(),
            "has_session_contexts",
            lambda target_session_id: target_session_id == session_id,
        )

        response = client.delete(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 400

    def test_orphan_running_세션은_delete시_self_heal후_삭제된다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "orphan 삭제 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")

        response = client.delete(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 204
        assert client.get(f"/api/v1/sessions/{session_id}").status_code == 404

    def test_종료된_세션은_노트_재생성을_요청할_수_있다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "재생성 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")
        artifact = build_session_recording_artifact(session_id, "system_audio")
        artifact.file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with wave.open(str(artifact.file_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(b"\x00\x00" * 800)

            client.post(f"/api/v1/sessions/{session_id}/end")
            response = client.post(f"/api/v1/sessions/{session_id}/reprocess")
            processing_response = client.get(f"/api/v1/sessions/{session_id}/processing")

            assert response.status_code == 200
            assert response.json()["post_processing_status"] == "queued"
            assert processing_response.status_code == 200
            assert processing_response.json()["latest_job_status"] == "pending"
        finally:
            shutil.rmtree(artifact.file_path.parent, ignore_errors=True)

    def test_orphan_running_세션은_노트_생성_요청시_self_heal후_후처리를_시작한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "orphan 재생성 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")
        artifact = build_session_recording_artifact(session_id, "system_audio")
        artifact.file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with wave.open(str(artifact.file_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(b"\x00\x00" * 800)

            response = client.post(f"/api/v1/sessions/{session_id}/reprocess")
            processing_response = client.get(f"/api/v1/sessions/{session_id}/processing")

            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "ended"
            assert payload["post_processing_status"] == "queued"
            assert payload["recovery_required"] is False
            assert processing_response.status_code == 200
            assert processing_response.json()["latest_job_status"] == "pending"
        finally:
            shutil.rmtree(artifact.file_path.parent, ignore_errors=True)

    def test_세션_종료시_미해결_참여자_followup을_조회할_수_있다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "참여자 후속 작업 테스트",
                "mode": "meeting",
                "source": "system_audio",
                "participants": ["박민수"],
            },
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")

        end_response = client.post(f"/api/v1/sessions/{session_id}/end")
        followups_response = client.get(f"/api/v1/sessions/{session_id}/participants/followups")

        assert end_response.status_code == 200
        assert followups_response.status_code == 200
        assert followups_response.json()["items"] == [
            {
                "id": followups_response.json()["items"][0]["id"],
                "session_id": session_id,
                "participant_order": 0,
                "participant_name": "박민수",
                "resolution_status": "unmatched",
                "followup_status": "pending",
                "matched_contact_count": 0,
                "contact_id": None,
                "account_id": None,
                "created_at": followups_response.json()["items"][0]["created_at"],
                "updated_at": followups_response.json()["items"][0]["updated_at"],
                "resolved_at": None,
                "resolved_by_user_id": None,
            }
        ]

    def test_이미_종료된_세션을_다시_종료해도_후처리_대기상태를_유지한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "중복 종료 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")

        first_end_response = client.post(f"/api/v1/sessions/{session_id}/end")
        second_end_response = client.post(f"/api/v1/sessions/{session_id}/end")

        assert first_end_response.status_code == 200
        assert second_end_response.status_code == 200
        assert first_end_response.json()["ended_at"] == second_end_response.json()["ended_at"]
        assert first_end_response.json()["post_processing_status"] == "queued"
        assert second_end_response.json()["post_processing_status"] == "queued"

        reports_response = client.get(f"/api/v1/reports/{session_id}")
        reports_payload = reports_response.json()
        assert reports_payload["items"] == []

    def test_mic_and_audio_소스로_세션을_생성할_수_있다(self, client):
        response = client.post(
            "/api/v1/sessions",
            json={
                "title": "혼합 입력 테스트",
                "mode": "meeting",
                "source": "mic_and_audio",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["primary_input_source"] == "mic_and_audio"

    def test_세션_참여자를_저장하고_목록에서도_유지한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "참여자 저장 테스트",
                "mode": "meeting",
                "source": "system_audio",
                "participants": ["김영희", "  박민수  ", "김영희", ""],
            },
        )

        assert create_response.status_code == 200
        created_payload = create_response.json()
        assert created_payload["participants"] == ["김영희", "박민수"]

        list_response = client.get("/api/v1/sessions")

        assert list_response.status_code == 200
        items = list_response.json()["items"]
        matched = next(item for item in items if item["id"] == created_payload["id"])
        assert matched["participants"] == ["김영희", "박민수"]

    def test_세션_참여자가_기존_contact와_자동으로_연결된다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "캡스 파트너스"},
        )
        account_id = account_response.json()["id"]
        contact_response = client.post(
            "/api/v1/context/contacts",
            json={
                "account_id": account_id,
                "name": "김영희",
                "job_title": "대리",
            },
        )
        contact_id = contact_response.json()["id"]

        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "참여자 연결 테스트",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
                "participants": ["김영희", "박민수"],
            },
        )

        assert create_response.status_code == 200
        payload = create_response.json()
        assert payload["participants"] == ["김영희", "박민수"]
        assert payload["participant_summary"] == {
            "total_count": 2,
            "linked_count": 1,
            "unmatched_count": 1,
            "ambiguous_count": 0,
            "unresolved_count": 1,
            "pending_followup_count": 0,
            "resolved_followup_count": 0,
        }
        detail_response = client.get(f"/api/v1/sessions/{payload['id']}/participants")
        detail_payload = detail_response.json()
        assert detail_payload["participants"][0] == {
            "name": "김영희",
            "normalized_name": "김영희",
            "contact_id": contact_id,
            "account_id": account_id,
            "email": None,
            "job_title": "대리",
            "department": None,
            "resolution_status": "linked",
        }
        assert detail_payload["participants"][1] == {
            "name": "박민수",
            "normalized_name": "박민수",
            "contact_id": None,
            "account_id": account_id,
            "email": None,
            "job_title": None,
            "department": None,
            "resolution_status": "unmatched",
        }
        assert detail_payload["participant_candidates"] == [
            {
                "name": "박민수",
                "account_id": account_id,
                "resolution_status": "unmatched",
                "matched_contact_count": 0,
                "matched_contacts": [],
            }
        ]

    def test_동명이인_contact가_여러_명이면_ambiguous_후보로_표시한다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "앰비규어스 테스트"},
        )
        account_id = account_response.json()["id"]
        client.post(
            "/api/v1/context/contacts",
            json={
                "account_id": account_id,
                "name": "김영희",
                "job_title": "매니저",
            },
        )
        client.post(
            "/api/v1/context/contacts",
            json={
                "account_id": account_id,
                "name": "김영희",
                "job_title": "리드",
            },
        )

        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "동명이인 테스트",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
                "participants": ["김영희"],
            },
        )

        assert create_response.status_code == 200
        payload = create_response.json()
        assert payload["participant_summary"] == {
            "total_count": 1,
            "linked_count": 0,
            "unmatched_count": 0,
            "ambiguous_count": 1,
            "unresolved_count": 1,
            "pending_followup_count": 0,
            "resolved_followup_count": 0,
        }
        detail_response = client.get(f"/api/v1/sessions/{payload['id']}/participants")
        detail_payload = detail_response.json()
        assert detail_payload["participants"] == [
            {
                "name": "김영희",
                "normalized_name": "김영희",
                "contact_id": None,
                "account_id": account_id,
                "email": None,
                "job_title": None,
                "department": None,
                "resolution_status": "ambiguous",
            }
        ]
        assert detail_payload["participant_candidates"] == [
            {
                "name": "김영희",
                "account_id": account_id,
                "resolution_status": "ambiguous",
                "matched_contact_count": 2,
                "matched_contacts": detail_payload["participant_candidates"][0]["matched_contacts"],
            }
        ]
        matched_contacts = detail_payload["participant_candidates"][0]["matched_contacts"]
        assert len(matched_contacts) == 2
        assert {item["job_title"] for item in matched_contacts} == {"매니저", "리드"}
        assert {item["department"] for item in matched_contacts} == {None}
        assert {item["name"] for item in matched_contacts} == {"김영희"}
        assert {item["account_id"] for item in matched_contacts} == {account_id}

    def test_세션_참여자_상세_api가_snapshot과_요약을_반환한다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "참여자 상세 테스트"},
        )
        account_id = account_response.json()["id"]
        contact_response = client.post(
            "/api/v1/context/contacts",
            json={
                "account_id": account_id,
                "name": "김영희",
                "email": "yh@example.com",
                "job_title": "매니저",
                "department": "사업개발팀",
            },
        )
        contact_id = contact_response.json()["id"]
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "참여자 상세 회의",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
                "participants": ["김영희", "박민수"],
            },
        )
        session_id = create_response.json()["id"]

        detail_response = client.get(f"/api/v1/sessions/{session_id}/participants")

        assert detail_response.status_code == 200
        payload = detail_response.json()
        assert payload["session_id"] == session_id
        assert payload["summary"] == {
            "total_count": 2,
            "linked_count": 1,
            "unmatched_count": 1,
            "ambiguous_count": 0,
            "unresolved_count": 1,
            "pending_followup_count": 0,
            "resolved_followup_count": 0,
        }
        assert payload["participants"] == [
            {
                "name": "김영희",
                "normalized_name": "김영희",
                "contact_id": contact_id,
                "account_id": account_id,
                "email": "yh@example.com",
                "job_title": "매니저",
                "department": "사업개발팀",
                "resolution_status": "linked",
            },
            {
                "name": "박민수",
                "normalized_name": "박민수",
                "contact_id": None,
                "account_id": account_id,
                "email": None,
                "job_title": None,
                "department": None,
                "resolution_status": "unmatched",
            },
        ]
        assert payload["participant_candidates"] == [
            {
                "name": "박민수",
                "account_id": account_id,
                "resolution_status": "unmatched",
                "matched_contact_count": 0,
                "matched_contacts": [],
            }
        ]

    def test_미연결_참여자를_contact로_승격하면_세션에_바로_연결된다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "참여자 승격 테스트"},
        )
        account_id = account_response.json()["id"]
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "참여자 승격 회의",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
                "participants": ["박민수"],
            },
        )
        session_id = create_response.json()["id"]

        promote_response = client.post(
            f"/api/v1/sessions/{session_id}/participants/contacts",
            json={
                "participant_name": "박민수",
                "email": "minsu@caps.local",
                "job_title": "대리",
                "department": "영업팀",
                "notes": "회의 참여자에서 승격",
            },
        )

        assert promote_response.status_code == 200
        payload = promote_response.json()
        assert payload["participant_summary"] == {
            "total_count": 1,
            "linked_count": 1,
            "unmatched_count": 0,
            "ambiguous_count": 0,
            "unresolved_count": 0,
            "pending_followup_count": 0,
            "resolved_followup_count": 0,
        }
        detail_response = client.get(f"/api/v1/sessions/{session_id}/participants")
        detail_payload = detail_response.json()
        assert detail_payload["participant_candidates"] == []
        assert detail_payload["participants"][0]["name"] == "박민수"
        assert detail_payload["participants"][0]["account_id"] == account_id
        assert detail_payload["participants"][0]["contact_id"] is not None
        assert detail_payload["participants"][0]["resolution_status"] == "linked"

        contacts_response = client.get(f"/api/v1/context/contacts?account_id={account_id}")
        assert contacts_response.status_code == 200
        contacts_payload = contacts_response.json()["items"]
        assert contacts_payload == [
            {
                "id": detail_payload["participants"][0]["contact_id"],
                "workspace_id": "workspace-default",
                "account_id": account_id,
                "name": "박민수",
                "email": "minsu@caps.local",
                "job_title": "대리",
                "department": "영업팀",
                "notes": "회의 참여자에서 승격",
                "status": "active",
                "created_by_user_id": None,
                "created_at": contacts_payload[0]["created_at"],
                "updated_at": contacts_payload[0]["updated_at"],
            }
        ]

    def test_종료된_세션에서_참여자를_contact로_승격하면_followup이_resolved_된다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "후속 작업 해결 테스트"},
        )
        account_id = account_response.json()["id"]
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "후속 작업 해결 회의",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
                "participants": ["박민수"],
            },
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")
        client.post(f"/api/v1/sessions/{session_id}/end")

        promote_response = client.post(
            f"/api/v1/sessions/{session_id}/participants/contacts",
            json={
                "participant_name": "박민수",
                "email": "minsu@caps.local",
                "job_title": "대리",
            },
        )
        followups_response = client.get(
            f"/api/v1/sessions/{session_id}/participants/followups?followup_status=resolved"
        )

        assert promote_response.status_code == 200
        assert followups_response.status_code == 200
        assert len(followups_response.json()["items"]) == 1
        assert followups_response.json()["items"][0]["participant_name"] == "박민수"
        assert followups_response.json()["items"][0]["followup_status"] == "resolved"
        detail_response = client.get(f"/api/v1/sessions/{session_id}/participants")
        assert followups_response.json()["items"][0]["contact_id"] == detail_response.json()[
            "participants"
        ][0]["contact_id"]

    def test_ambiguous_참여자는_contact_승격을_거부한다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "승격 거부 테스트"},
        )
        account_id = account_response.json()["id"]
        client.post(
            "/api/v1/context/contacts",
            json={"account_id": account_id, "name": "김영희"},
        )
        client.post(
            "/api/v1/context/contacts",
            json={"account_id": account_id, "name": "김영희"},
        )
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "승격 거부 회의",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
                "participants": ["김영희"],
            },
        )
        session_id = create_response.json()["id"]

        promote_response = client.post(
            f"/api/v1/sessions/{session_id}/participants/contacts",
            json={"participant_name": "김영희"},
        )

        assert promote_response.status_code == 400
        assert "자동 승격" in promote_response.json()["detail"]

    def test_ambiguous_참여자를_기존_contact로_연결할_수_있다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "기존 contact 연결 테스트"},
        )
        account_id = account_response.json()["id"]
        first_contact = client.post(
            "/api/v1/context/contacts",
            json={"account_id": account_id, "name": "김영희", "job_title": "매니저"},
        ).json()
        client.post(
            "/api/v1/context/contacts",
            json={"account_id": account_id, "name": "김영희", "job_title": "리드"},
        )
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "기존 contact 연결 회의",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
                "participants": ["김영희"],
            },
        )
        session_id = create_response.json()["id"]

        link_response = client.post(
            f"/api/v1/sessions/{session_id}/participants/links",
            json={
                "participant_name": "김영희",
                "contact_id": first_contact["id"],
            },
        )

        assert link_response.status_code == 200
        payload = link_response.json()
        assert payload["participant_summary"] == {
            "total_count": 1,
            "linked_count": 1,
            "unmatched_count": 0,
            "ambiguous_count": 0,
            "unresolved_count": 0,
            "pending_followup_count": 0,
            "resolved_followup_count": 0,
        }
        detail_response = client.get(f"/api/v1/sessions/{session_id}/participants")
        detail_payload = detail_response.json()
        assert detail_payload["participant_candidates"] == []
        assert detail_payload["participants"] == [
            {
                "name": "김영희",
                "normalized_name": "김영희",
                "contact_id": first_contact["id"],
                "account_id": account_id,
                "email": None,
                "job_title": "매니저",
                "department": None,
                "resolution_status": "linked",
            }
        ]

    def test_ambiguous_참여자_후보에_없는_contact는_연결할_수_없다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "잘못된 연결 테스트"},
        )
        account_id = account_response.json()["id"]
        client.post(
            "/api/v1/context/contacts",
            json={"account_id": account_id, "name": "김영희", "job_title": "매니저"},
        )
        client.post(
            "/api/v1/context/contacts",
            json={"account_id": account_id, "name": "김영희", "job_title": "리드"},
        )
        other_contact = client.post(
            "/api/v1/context/contacts",
            json={"account_id": account_id, "name": "박민수", "job_title": "대리"},
        ).json()
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "잘못된 연결 회의",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
                "participants": ["김영희"],
            },
        )
        session_id = create_response.json()["id"]

        link_response = client.post(
            f"/api/v1/sessions/{session_id}/participants/links",
            json={
                "participant_name": "김영희",
                "contact_id": other_contact["id"],
            },
        )

        assert link_response.status_code == 400
        assert "ambiguous 후보 목록" in link_response.json()["detail"]
