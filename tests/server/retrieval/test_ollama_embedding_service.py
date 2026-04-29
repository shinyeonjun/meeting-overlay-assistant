import json

import pytest

from server.app.services.retrieval.embedding.ollama_embedding_service import (
    OllamaEmbeddingService,
)


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_ollama_embedding_service_validates_expected_dimensions(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return _FakeResponse({"embeddings": [[0.1, 0.2, 0.3]]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    service = OllamaEmbeddingService(
        base_url="http://127.0.0.1:11434",
        model="fake-model",
        expected_dimensions=2,
    )

    with pytest.raises(RuntimeError, match="embedding 차원"):
        service.embed(["검색어"])


def test_ollama_embedding_service_accepts_matching_dimensions(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return _FakeResponse({"embeddings": [[0.1, 0.2]]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    service = OllamaEmbeddingService(
        base_url="http://127.0.0.1:11434",
        model="fake-model",
        expected_dimensions=2,
    )

    assert service.embed(["검색어"]) == [[0.1, 0.2]]
