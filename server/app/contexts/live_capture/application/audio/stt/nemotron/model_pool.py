"""Nemotron 모델 인스턴스 풀.

한 모델 인스턴스를 여러 스트림이 동시에 generate()하면 내부 상태가 섞여 죽는다.
그래서 스트림(세션)마다 인스턴스 하나를 빌려 쓰고, 세션이 끝나면 돌려받아 다음 세션이 다시 쓴다.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NemotronModelKey:
    """같은 풀을 공유하는 모델 설정."""

    model_ref: str
    device: str
    dtype: str
    lookahead_tokens: int


@dataclass
class NemotronModelSlot:
    """빌려 주는 단위. processor도 lookahead 설정을 들고 있어 슬롯마다 따로 둔다."""

    model: Any
    processor: Any


def load_nemotron_slot(key: NemotronModelKey) -> NemotronModelSlot:
    """transformers로 모델과 processor를 올린다."""

    import torch
    from transformers import AutoModelForRNNT, AutoProcessor

    processor = AutoProcessor.from_pretrained(key.model_ref)
    processor.set_num_lookahead_tokens(key.lookahead_tokens)
    model = AutoModelForRNNT.from_pretrained(
        key.model_ref,
        device_map=key.device,
        dtype=getattr(torch, key.dtype),
    )
    model.eval()
    return NemotronModelSlot(model=model, processor=processor)


class NemotronModelPool:
    """빌려 준 슬롯은 반납 전까지 다른 스트림에 주지 않는다."""

    def __init__(self, key: NemotronModelKey, *, loader=load_nemotron_slot) -> None:
        self._key = key
        self._loader = loader
        self._idle: list[NemotronModelSlot] = []
        self._loaded_count = 0
        self._lock = Lock()

    @property
    def loaded_count(self) -> int:
        return self._loaded_count

    @property
    def idle_count(self) -> int:
        with self._lock:
            return len(self._idle)

    def acquire(self) -> NemotronModelSlot:
        with self._lock:
            if self._idle:
                return self._idle.pop()
        slot = self._loader(self._key)
        with self._lock:
            self._loaded_count += 1
            loaded_count = self._loaded_count
        logger.info(
            "Nemotron 모델 인스턴스 로드: model=%s device=%s dtype=%s 누적=%s",
            self._key.model_ref,
            self._key.device,
            self._key.dtype,
            loaded_count,
        )
        return slot

    def release(self, slot: NemotronModelSlot) -> None:
        with self._lock:
            self._idle.append(slot)


_POOLS: dict[NemotronModelKey, NemotronModelPool] = {}
_POOLS_LOCK = Lock()


def get_nemotron_model_pool(key: NemotronModelKey) -> NemotronModelPool:
    """설정별 공용 풀을 돌려준다."""

    with _POOLS_LOCK:
        pool = _POOLS.get(key)
        if pool is None:
            pool = NemotronModelPool(key)
            _POOLS[key] = pool
        return pool


def clear_nemotron_model_pools() -> None:
    """테스트용: 공용 풀을 비운다."""

    with _POOLS_LOCK:
        _POOLS.clear()
