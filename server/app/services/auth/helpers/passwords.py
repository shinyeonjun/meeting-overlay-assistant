"""인증 영역의 passwords 서비스를 제공한다."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordHashParts:
    """저장용 비밀번호 해시 구성 요소."""

    iterations: int
    salt: bytes
    digest: bytes


def hash_password(
    password: str,
    *,
    password_normalizer,
    algorithm: str,
    iterations: int,
) -> str:
    """비밀번호를 PBKDF2 해시로 변환한다."""

    normalized_password = password_normalizer(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        algorithm,
        normalized_password.encode("utf-8"),
        salt,
        iterations,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_{algorithm}${iterations}${salt_b64}${digest_b64}"


def verify_password(
    password: str,
    stored_hash: str,
    *,
    password_normalizer,
    algorithm: str,
    invalid_credentials_error_type: type[Exception],
) -> bool:
    """비밀번호와 저장된 해시가 일치하는지 확인한다."""

    normalized_password = password_normalizer(password)
    parts = parse_password_hash(
        stored_hash,
        algorithm=algorithm,
        invalid_credentials_error_type=invalid_credentials_error_type,
    )
    computed_digest = hashlib.pbkdf2_hmac(
        algorithm,
        normalized_password.encode("utf-8"),
        parts.salt,
        parts.iterations,
    )
    return hmac.compare_digest(parts.digest, computed_digest)


def parse_password_hash(
    stored_hash: str,
    *,
    algorithm: str,
    invalid_credentials_error_type: type[Exception],
) -> PasswordHashParts:
    """저장된 비밀번호 해시 문자열을 파싱한다."""

    try:
        raw_algorithm, raw_iterations, raw_salt, raw_digest = stored_hash.split(
            "$",
            maxsplit=3,
        )
    except ValueError as error:
        raise invalid_credentials_error_type(
            "저장된 비밀번호 해시 형식이 올바르지 않습니다."
        ) from error

    if raw_algorithm != f"pbkdf2_{algorithm}":
        raise invalid_credentials_error_type("지원하지 않는 비밀번호 해시 알고리즘입니다.")

    return PasswordHashParts(
        iterations=int(raw_iterations),
        salt=base64.b64decode(raw_salt.encode("ascii")),
        digest=base64.b64decode(raw_digest.encode("ascii")),
    )


def hash_token(token: str) -> str:
    """액세스 토큰을 저장용 해시로 변환한다."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
