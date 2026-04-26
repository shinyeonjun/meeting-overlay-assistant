"""식별자 생성과 레거시 식별자 변환 helper."""

from __future__ import annotations

from hashlib import md5
from string import hexdigits
from uuid import UUID, uuid4


def generate_uuid_str() -> str:
    """새 UUID 문자열을 생성한다."""

    return str(uuid4())


def legacy_text_to_uuid_str(value: str) -> str:
    """레거시 문자열 식별자를 UUID 문자열로 정규화한다."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("식별자 값이 비어 있습니다.")

    try:
        return str(UUID(normalized))
    except ValueError:
        pass

    compact = normalized.replace("-", "")
    if len(compact) == 32 and all(character in hexdigits for character in compact):
        return str(UUID(compact))

    suffix = normalized.rsplit("-", maxsplit=1)[-1]
    if len(suffix) == 32 and all(character in hexdigits for character in suffix):
        return str(UUID(suffix))

    return str(UUID(md5(normalized.encode("utf-8")).hexdigest()))
