"""Ollama embedding 서비스."""

from __future__ import annotations

import json
from urllib import request


class OllamaEmbeddingService:
    """Ollama /api/embed를 이용해 텍스트 embedding을 생성한다."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: int = 20,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """여러 텍스트를 한 번에 embedding한다."""

        normalized_texts = [text.strip() for text in texts if text.strip()]
        if not normalized_texts:
            return []

        payload = json.dumps(
            {
                "model": self._model,
                "input": normalized_texts,
                "truncate": True,
            }
        ).encode("utf-8")
        http_request = request.Request(
            url=f"{self._base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
        parsed = json.loads(raw_body)

        embeddings = parsed.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            return [[float(value) for value in item] for item in embeddings]

        single_embedding = parsed.get("embedding")
        if isinstance(single_embedding, list):
            return [[float(value) for value in single_embedding]]

        raise RuntimeError("Ollama embedding 응답 형식을 해석할 수 없습니다.")
