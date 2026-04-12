"""세션 API 테스트"""


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

        reports_response = client.get(f"/api/v1/reports/{session_id}")
        reports_payload = reports_response.json()
        assert reports_response.status_code == 200
        assert reports_payload["items"] == []

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

    def test_이미_종료된_세션을_다시_종료해도_리포트가_자동_생성되지_않는다(self, client):
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
