"""서버 설정 CLI 테스트."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json

import pytest

import server.scripts.admin.setup_server as setup_server_module


class TestSetupServerCli:
    """서버 설정 CLI 흐름을 검증한다."""

    def test_멤버를_cli로_추가하고_역할을_변경할_수_있다(self, isolated_database, capsys):
        bootstrap_args = argparse.Namespace(
            login_id="owner",
            display_name="관리자",
            password="password123!",
            job_title="대표",
            department="운영팀",
            output="json",
        )
        add_member_args = argparse.Namespace(
            login_id="member",
            display_name="영업 담당",
            password="password123!",
            role="member",
            job_title="대리",
            department="영업팀",
            output="json",
        )
        change_role_args = argparse.Namespace(
            login_id="member",
            role="admin",
            output="json",
        )

        assert setup_server_module.bootstrap_admin(bootstrap_args) == 0
        bootstrap_output = json.loads(capsys.readouterr().out)
        assert bootstrap_output["workspace_role"] == "owner"

        assert setup_server_module.add_member(add_member_args) == 0
        add_member_output = json.loads(capsys.readouterr().out)
        assert add_member_output["login_id"] == "member"
        assert add_member_output["workspace_role"] == "member"

        assert setup_server_module.change_member_role(change_role_args) == 0
        change_role_output = json.loads(capsys.readouterr().out)
        assert change_role_output["workspace_role"] == "admin"

        assert setup_server_module.list_members("json") == 0
        members_output = json.loads(capsys.readouterr().out)
        member_row = next(item for item in members_output if item["login_id"] == "member")
        assert member_row["workspace_role"] == "admin"

    def test_존재하지_않는_멤버_역할_변경은_cli에서_실패한다(
        self,
        isolated_database,
        capsys,
    ):
        bootstrap_args = argparse.Namespace(
            login_id="owner",
            display_name="관리자",
            password="password123!",
            job_title="대표",
            department="운영팀",
            output="json",
        )
        missing_role_args = argparse.Namespace(
            login_id="ghost",
            role="admin",
            output="json",
        )

        assert setup_server_module.bootstrap_admin(bootstrap_args) == 0
        capsys.readouterr()

        assert setup_server_module.change_member_role(missing_role_args) == 1
        captured = capsys.readouterr()
        assert "대상 사용자를 찾지 못했습니다." in captured.err

    def test_text_output이_운영자_친화적으로_정리된다(self, isolated_database, capsys):
        bootstrap_args = argparse.Namespace(
            login_id="owner",
            display_name="관리자",
            password="password123!",
            job_title="대표",
            department="운영팀",
            output="json",
        )
        add_member_args = argparse.Namespace(
            login_id="member",
            display_name="영업 담당",
            password="password123!",
            role="member",
            job_title="대리",
            department="영업팀",
            output="json",
        )

        assert setup_server_module.bootstrap_admin(bootstrap_args) == 0
        capsys.readouterr()
        assert setup_server_module.add_member(add_member_args) == 0
        capsys.readouterr()

        assert setup_server_module.list_members("text") == 0
        list_output = capsys.readouterr().out
        assert "워크스페이스 멤버 목록" in list_output
        assert "영업 담당" in list_output
        assert "member" in list_output

        assert setup_server_module.print_status("text") == 0
        status_output = capsys.readouterr().out
        assert "서버 상태" in status_output
        assert "관리자" in status_output

    def test_dashboard_snapshot이_개요와_진단을_보여준다(self, isolated_database, capsys):
        bootstrap_args = argparse.Namespace(
            login_id="owner",
            display_name="관리자",
            password="password123!",
            job_title="대표",
            department="운영팀",
            output="json",
        )
        assert setup_server_module.bootstrap_admin(bootstrap_args) == 0
        capsys.readouterr()

        monitor_service = setup_server_module.get_runtime_monitor_service()
        monitor_service.reset()
        monitor_service.record_chunk_processed(
            session_id="session-123",
            utterance_count=2,
            event_count=1,
        )
        monitor_service.record_final_transcription(
            session_id="session-123",
            final_queue_delay_ms=1800,
            emitted_live_final=True,
            alignment_status="matched",
        )

        assert setup_server_module.print_dashboard_snapshot("text") == 0
        dashboard_output = capsys.readouterr().out
        assert "CAPS 운영 대시보드" in dashboard_output
        assert "개요" in dashboard_output
        assert "운영 진단" in dashboard_output
        assert "설정 요약" in dashboard_output
        assert "오디오 파이프라인 모니터" in dashboard_output
        assert "멤버 미리보기" in dashboard_output

    def test_doctor는_서버가_없을때_진단_메시지를_보여준다(self, isolated_database, capsys):
        assert setup_server_module.print_doctor(
            "text",
            host_address="127.0.0.1",
            port=65500,
        ) == 0
        output = capsys.readouterr().out
        assert "운영 진단" in output
        assert "연결" in output
        assert "진단 가이드" in output

    def test_logs는_최근_로그를_출력한다(self, isolated_database, tmp_path, monkeypatch, capsys):
        log_path = tmp_path / "caps-server.log"
        log_path.write_text("첫 줄\n둘째 줄\n셋째 줄\n", encoding="utf-8")
        monkeypatch.setattr(
            setup_server_module,
            "settings",
            replace(setup_server_module.settings, log_file_path=log_path),
        )

        assert setup_server_module.print_logs("text", lines=2, follow=False, interval=1.0) == 0
        output = capsys.readouterr().out
        assert "live logs" in output
        assert "둘째 줄" in output
        assert "셋째 줄" in output
        assert "첫 줄" not in output

    def test_settings_프리셋은_env에_기록된다(self, isolated_database, tmp_path, monkeypatch, capsys):
        env_example_path = tmp_path / ".env.example"
        env_example_path.write_text(
            "\n".join(
                [
                    "SERVER_HOST=127.0.0.1",
                    "SERVER_PORT=8011",
                    "AUTH_ENABLED=false",
                    "LOG_LEVEL=INFO",
                    "STT_BACKEND=faster_whisper_streaming",
                    "STT_BACKEND_SYSTEM_AUDIO=hybrid_local_streaming_sherpa",
                    "STT_DEVICE=auto",
                    "STT_COMPUTE_TYPE=default",
                    "STT_BASE_URL=",
                    "RYZEN_AI_INSTALLATION_PATH=",
                    "SPEAKER_DIARIZER_BACKEND=unknown_speaker",
                    "SPEAKER_DIARIZER_DEVICE=cpu",
                    "LLM_BASE_URL=http://127.0.0.1:11434/v1",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env_path = tmp_path / ".env"
        monkeypatch.setattr(setup_server_module, "ENV_EXAMPLE_PATH", env_example_path)
        monkeypatch.setattr(setup_server_module, "ENV_FILE_PATH", env_path)

        args = argparse.Namespace(
            preset="cuda-local",
            interactive=False,
            server_host="0.0.0.0",
            server_port=9011,
            auth_enabled="true",
            log_level="DEBUG",
            stt_backend=None,
            stt_system_backend=None,
            stt_device=None,
            stt_compute_type=None,
            stt_base_url=None,
            ryzen_ai_path=None,
            speaker_diarizer_backend=None,
            speaker_diarizer_device=None,
            llm_base_url=None,
            save_profile=None,
            output="json",
        )

        assert setup_server_module.apply_settings(args) == 0
        payload = json.loads(capsys.readouterr().out)
        env_text = env_path.read_text(encoding="utf-8")
        assert payload["server_host"] == "0.0.0.0"
        assert payload["server_port"] == "9011"
        assert payload["auth_enabled"] == "true"
        assert "SERVER_PORT=9011" in env_text
        assert "STT_DEVICE=cuda" in env_text
        assert "STT_COMPUTE_TYPE=int8_float16" in env_text

    def test_profiles는_저장_적용_삭제를_지원한다(self, isolated_database, tmp_path, monkeypatch, capsys):
        env_example_path = tmp_path / ".env.example"
        env_example_path.write_text(
            "\n".join(
                [
                    "SERVER_HOST=127.0.0.1",
                    "SERVER_PORT=8011",
                    "AUTH_ENABLED=false",
                    "LOG_LEVEL=INFO",
                    "STT_BACKEND=faster_whisper_streaming",
                    "STT_BACKEND_SYSTEM_AUDIO=hybrid_local_streaming_sherpa",
                    "STT_MODEL_ID=deepdml/faster-whisper-large-v3-turbo-ct2",
                    "STT_DEVICE=auto",
                    "STT_COMPUTE_TYPE=default",
                    "STT_BASE_URL=",
                    "STT_ENCODER_MODEL_PATH=",
                    "STT_DECODER_MODEL_PATH=",
                    "STT_PRELOAD_ON_STARTUP=true",
                    "ANALYZER_BACKEND=rule_based",
                    "RYZEN_AI_INSTALLATION_PATH=",
                    "SPEAKER_DIARIZER_BACKEND=unknown_speaker",
                    "SPEAKER_DIARIZER_DEVICE=cpu",
                    "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH=server/scripts/workers/pyannote_worker.py",
                    "LLM_BASE_URL=http://127.0.0.1:11434/v1",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env_path = tmp_path / ".env"
        profile_dir = tmp_path / "profiles"
        monkeypatch.setattr(setup_server_module, "ENV_EXAMPLE_PATH", env_example_path)
        monkeypatch.setattr(setup_server_module, "ENV_FILE_PATH", env_path)
        monkeypatch.setattr(setup_server_module, "SETTINGS_PROFILE_DIR", profile_dir)

        apply_args = argparse.Namespace(
            preset="cuda-local",
            interactive=False,
            server_host="0.0.0.0",
            server_port=9011,
            auth_enabled="true",
            log_level="DEBUG",
            stt_backend=None,
            stt_system_backend=None,
            stt_device=None,
            stt_compute_type=None,
            stt_base_url=None,
            ryzen_ai_path=None,
            speaker_diarizer_backend=None,
            speaker_diarizer_device=None,
            llm_base_url=None,
            save_profile=None,
            output="json",
        )
        assert setup_server_module.apply_settings(apply_args) == 0
        capsys.readouterr()

        save_args = argparse.Namespace(action="save", name="office-cuda", note="GPU 기본 세팅", output="json")
        assert setup_server_module.manage_profiles(save_args) == 0
        save_payload = json.loads(capsys.readouterr().out)
        assert save_payload["name"] == "office-cuda"
        assert (profile_dir / "office-cuda.json").exists()

        drift_args = argparse.Namespace(
            preset=None,
            interactive=False,
            server_host="127.0.0.1",
            server_port=7777,
            auth_enabled="false",
            log_level="INFO",
            stt_backend="faster_whisper_streaming",
            stt_system_backend=None,
            stt_device="cpu",
            stt_compute_type="int8",
            stt_base_url=None,
            ryzen_ai_path=None,
            speaker_diarizer_backend=None,
            speaker_diarizer_device=None,
            llm_base_url=None,
            save_profile=None,
            output="json",
        )
        assert setup_server_module.apply_settings(drift_args) == 0
        capsys.readouterr()

        apply_profile_args = argparse.Namespace(action="apply", name="office-cuda", note=None, output="json")
        assert setup_server_module.manage_profiles(apply_profile_args) == 0
        apply_payload = json.loads(capsys.readouterr().out)
        assert apply_payload["name"] == "office-cuda"
        env_text = env_path.read_text(encoding="utf-8")
        assert "SERVER_PORT=9011" in env_text
        assert "STT_DEVICE=cuda" in env_text
        assert "SERVER_SETTINGS_PROFILE=office-cuda" in env_text

        delete_args = argparse.Namespace(action="delete", name="office-cuda", note=None, output="json")
        assert setup_server_module.manage_profiles(delete_args) == 0
        delete_payload = json.loads(capsys.readouterr().out)
        assert delete_payload["deleted"] is True
        assert not (profile_dir / "office-cuda.json").exists()

    def test_doctor는_하드웨어_체크를_포함한다(self, isolated_database, tmp_path, monkeypatch):
        env_example_path = tmp_path / ".env.example"
        env_example_path.write_text(
            "\n".join(
                [
                    "SERVER_HOST=127.0.0.1",
                    "SERVER_PORT=8011",
                    "AUTH_ENABLED=false",
                    "LOG_LEVEL=INFO",
                    "STT_BACKEND=amd_whisper_npu",
                    "STT_BACKEND_SYSTEM_AUDIO=hybrid_local_streaming_sherpa",
                    "STT_MODEL_ID=amd/whisper-small-onnx-npu",
                    "STT_DEVICE=auto",
                    "STT_COMPUTE_TYPE=default",
                    "STT_BASE_URL=",
                    "STT_ENCODER_MODEL_PATH=C:\\missing\\encoder.onnx",
                    "STT_DECODER_MODEL_PATH=C:\\missing\\decoder.onnx",
                    "RYZEN_AI_INSTALLATION_PATH=C:\\missing\\ryzen",
                    "SPEAKER_DIARIZER_BACKEND=unknown_speaker",
                    "SPEAKER_DIARIZER_DEVICE=cpu",
                    "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH=server/scripts/workers/pyannote_worker.py",
                    "LLM_BASE_URL=",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(setup_server_module, "ENV_EXAMPLE_PATH", env_example_path)
        monkeypatch.setattr(setup_server_module, "ENV_FILE_PATH", tmp_path / ".env")

        payload = setup_server_module.build_doctor_payload(host_address="127.0.0.1", port=65500)
        labels = {item["label"]: item["status"] for item in payload["checks"]}
        assert labels["RyzenAI 경로"] == "fail"
        assert labels["AMD encoder"] == "fail"
        assert labels["AMD decoder"] == "fail"

    def test_dashboard는_q입력으로_종료한다(self, isolated_database, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _prompt="": "q")
        args = argparse.Namespace(
            once=False,
            output="text",
            host_address="127.0.0.1",
            port=8011,
            log_lines=18,
        )

        assert setup_server_module.run_dashboard(args) == 0
        dashboard_output = capsys.readouterr().out
        assert "CAPS 운영 대시보드" in dashboard_output
        assert "대시보드를 종료합니다." in dashboard_output

    def test_dashboard에서_live_logs_화면으로_들어갈_수_있다(
        self,
        isolated_database,
        tmp_path,
        monkeypatch,
        capsys,
    ):
        log_path = tmp_path / "caps-server.log"
        log_path.write_text("로그 한 줄\n로그 두 줄\n", encoding="utf-8")
        monkeypatch.setattr(
            setup_server_module,
            "settings",
            replace(setup_server_module.settings, log_file_path=log_path),
        )
        answers = iter(["6", "q", "q"])
        monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
        args = argparse.Namespace(
            once=False,
            output="text",
            host_address="127.0.0.1",
            port=8011,
            log_lines=18,
        )

        assert setup_server_module.run_dashboard(args) == 0
        output = capsys.readouterr().out
        assert "live logs" in output
        assert "로그 두 줄" in output

    def test_dashboard에서_settings_마법사를_실행할_수_있다(
        self,
        isolated_database,
        tmp_path,
        monkeypatch,
        capsys,
    ):
        env_example_path = tmp_path / ".env.example"
        env_example_path.write_text(
            "\n".join(
                [
                    "SERVER_HOST=127.0.0.1",
                    "SERVER_PORT=8011",
                    "AUTH_ENABLED=false",
                    "LOG_LEVEL=INFO",
                    "STT_BACKEND=faster_whisper_streaming",
                    "STT_BACKEND_SYSTEM_AUDIO=hybrid_local_streaming_sherpa",
                    "STT_DEVICE=auto",
                    "STT_COMPUTE_TYPE=default",
                    "STT_BASE_URL=",
                    "RYZEN_AI_INSTALLATION_PATH=",
                    "SPEAKER_DIARIZER_BACKEND=unknown_speaker",
                    "SPEAKER_DIARIZER_DEVICE=cpu",
                    "LLM_BASE_URL=http://127.0.0.1:11434/v1",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env_path = tmp_path / ".env"
        monkeypatch.setattr(setup_server_module, "ENV_EXAMPLE_PATH", env_example_path)
        monkeypatch.setattr(setup_server_module, "ENV_FILE_PATH", env_path)

        answers = iter(
            [
                "7",
                "",
                "0.0.0.0",
                "9011",
                "y",
                "DEBUG",
                "",
                "",
                "",
                "",
                "n",
                "q",
            ]
        )
        monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
        args = argparse.Namespace(
            once=False,
            output="text",
            host_address="127.0.0.1",
            port=8011,
            log_lines=18,
        )

        assert setup_server_module.run_dashboard(args) == 0
        output = capsys.readouterr().out
        env_text = env_path.read_text(encoding="utf-8")
        assert "설정 적용 결과" in output
        assert "대시보드를 종료합니다." in output
        assert "SERVER_PORT=9011" in env_text
        assert "AUTH_ENABLED=true" in env_text

    def test_dashboard에서_profiles_화면으로_들어갈_수_있다(
        self,
        isolated_database,
        tmp_path,
        monkeypatch,
        capsys,
    ):
        monkeypatch.setattr(setup_server_module, "SETTINGS_PROFILE_DIR", tmp_path / "profiles")
        setup_server_module._save_settings_profile("default-local", note="기본 복구점")
        answers = iter(["8", "q", "q"])
        monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
        args = argparse.Namespace(
            once=False,
            output="text",
            host_address="127.0.0.1",
            port=8011,
            log_lines=18,
        )

        assert setup_server_module.run_dashboard(args) == 0
        output = capsys.readouterr().out
        assert "설정 프로필" in output
        assert "default-local" in output

    @pytest.mark.parametrize(
        ("role_input", "expected"),
        [
            ("", "member"),
            ("admin", "admin"),
        ],
    )
    def test_대시보드_역할_입력은_기본값을_지원한다(self, monkeypatch, role_input, expected):
        monkeypatch.setattr("builtins.input", lambda _prompt="": role_input)
        assert setup_server_module._prompt_role(default="member") == expected
