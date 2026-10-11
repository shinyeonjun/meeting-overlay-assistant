"""발화 생성 시 기본 불변식(시간 순서, 순번)을 검사한다."""

from __future__ import annotations

import pytest

from server.app.domain.models.utterance import Utterance


def _create(**overrides):
    values = dict(
        session_id="session-1",
        seq_num=1,
        start_ms=0,
        end_ms=1000,
        text="회의 내용",
        confidence=0.9,
    )
    values.update(overrides)
    return Utterance.create(**values)


def test_정상_발화는_생성된다():
    utterance = _create()

    assert utterance.start_ms == 0
    assert utterance.end_ms == 1000


def test_끝_시각이_시작보다_빠르면_거부한다():
    with pytest.raises(ValueError, match="시간 범위"):
        _create(start_ms=2000, end_ms=1000)


def test_음수_시작_시각은_거부한다():
    with pytest.raises(ValueError, match="시간 범위"):
        _create(start_ms=-1, end_ms=10)


def test_순번이_1보다_작으면_거부한다():
    with pytest.raises(ValueError, match="순번"):
        _create(seq_num=0)


def test_시작과_끝이_같은_발화는_허용한다():
    utterance = _create(start_ms=500, end_ms=500)

    assert utterance.start_ms == utterance.end_ms
