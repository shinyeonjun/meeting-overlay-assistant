"""GPU execution gate 테스트."""

from __future__ import annotations

import pytest

from server.app.infrastructure.persistence.postgresql.gpu_execution_gate import (
    PostgreSQLGpuExecutionGate,
)


def test_gpu_execution_gate는_동일한_lock_key를_직렬화한다(isolated_database):
    first_gate = PostgreSQLGpuExecutionGate(
        isolated_database,
        lock_key=915001,
        default_poll_interval_seconds=0.01,
    )
    second_gate = PostgreSQLGpuExecutionGate(
        isolated_database,
        lock_key=915001,
        default_poll_interval_seconds=0.01,
    )

    with first_gate.hold(owner="first", timeout_seconds=0.1):
        with pytest.raises(TimeoutError):
            with second_gate.hold(
                owner="second",
                timeout_seconds=0.05,
                poll_interval_seconds=0.01,
            ):
                pass


def test_gpu_execution_gate는_release_이후_다시_획득할_수_있다(isolated_database):
    gate = PostgreSQLGpuExecutionGate(
        isolated_database,
        lock_key=915002,
        default_poll_interval_seconds=0.01,
    )

    with gate.hold(owner="first", timeout_seconds=0.1):
        pass

    with gate.hold(owner="second", timeout_seconds=0.1):
        pass
