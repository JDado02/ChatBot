import math

import httpx
import pytest

from app.embeddings import HashEmbedder, OllamaEmbedder
from app.vectors import cosine_similarity


# --- HashEmbedder (deterministico, offline) ---------------------------------

def test_hash_embedder_dim():
    emb = HashEmbedder(dim=1024)
    out = emb.embed(["ciao"])
    assert len(out) == 1
    assert len(out[0]) == 1024


def test_hash_embedder_custom_dim():
    assert len(HashEmbedder(dim=37).embed(["x"])[0]) == 37


def test_hash_embedder_deterministic():
    emb = HashEmbedder(dim=64)
    a = emb.embed(["stessa frase"])[0]
    b = emb.embed(["stessa frase"])[0]
    assert a == b


def test_hash_embedder_different_texts_differ():
    emb = HashEmbedder(dim=64)
    a = emb.embed(["colazione"])[0]
    b = emb.embed(["parcheggio"])[0]
    assert a != b


def test_hash_embedder_normalized():
    v = HashEmbedder(dim=128).embed(["qualcosa"])[0]
    norm = math.sqrt(sum(x * x for x in v))
    assert norm == pytest.approx(1.0, abs=1e-9)


def test_hash_embedder_batch():
    out = HashEmbedder(dim=16).embed(["a", "b", "c"])
    assert len(out) == 3


def test_hash_embedder_identical_text_cosine_one():
    # Fondamento della ricerca: testo identico -> vettori identici -> coseno 1.
    emb = HashEmbedder(dim=256)
    q = emb.embed(["a che ora è la colazione?"])[0]
    d = emb.embed(["a che ora è la colazione?"])[0]
    assert cosine_similarity(q, d) == pytest.approx(1.0)


# --- OllamaEmbedder (con trasporto HTTP finto) ------------------------------

def _mock_transport(vector):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embedding": vector})
    return httpx.MockTransport(handler)


def test_ollama_embedder_parses_response():
    emb = OllamaEmbedder("http://x", "bge-m3", dim=8, transport=_mock_transport([0.1] * 8))
    out = emb.embed(["ciao", "mondo"])
    assert len(out) == 2
    assert out[0] == pytest.approx([0.1] * 8)


def test_ollama_embedder_dim_mismatch_raises():
    emb = OllamaEmbedder("http://x", "bge-m3", dim=8, transport=_mock_transport([0.1] * 4))
    with pytest.raises(ValueError):
        emb.embed(["x"])


def test_ollama_embedder_missing_field_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"nope": []})
    emb = OllamaEmbedder("http://x", "bge-m3", dim=8, transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError):
        emb.embed(["x"])
