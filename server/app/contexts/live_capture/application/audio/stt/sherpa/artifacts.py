"""sherpa-onnx transducer 아티팩트 해석 helper."""

from __future__ import annotations

from pathlib import Path


def resolve_transducer_artifacts(model_dir: Path) -> dict[str, Path]:
    """모델 디렉터리에서 sherpa transducer 아티팩트를 찾는다."""

    candidates = {
        "tokens": ("tokens.txt",),
        "encoder": ("encoder*.onnx",),
        "decoder": ("decoder*.onnx",),
        "joiner": ("joiner*.onnx",),
    }
    resolved: dict[str, Path] = {}
    for key, patterns in candidates.items():
        for pattern in patterns:
            matches = sort_artifact_matches(key, model_dir.glob(pattern))
            if matches:
                resolved[key] = matches[0].resolve()
                break
        if key not in resolved:
            raise RuntimeError(
                f"sherpa-onnx 모델 파일을 찾지 못했습니다. key={key} dir={model_dir}"
            )
    return resolved


def sort_artifact_matches(key: str, matches) -> list[Path]:
    """아티팩트 후보를 우선순위에 맞게 정렬한다."""

    paths = [path.resolve() for path in matches]

    def sort_key(path: Path) -> tuple[int, str]:
        name = path.name.casefold()
        is_int8 = ".int8." in name
        if key == "decoder":
            return (1 if is_int8 else 0, name)
        if key in {"encoder", "joiner"}:
            return (0 if is_int8 else 1, name)
        return (0, name)

    return sorted(paths, key=sort_key)

