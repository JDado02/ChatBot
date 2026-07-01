import math

import pytest

from app.vectors import to_pgvector, parse_pgvector, cosine_similarity


def test_to_pgvector_format():
    assert to_pgvector([1, 2, 3]) == "[1.0,2.0,3.0]"


def test_to_pgvector_roundtrip():
    vec = [0.1, -0.25, 3.0, 0.0]
    parsed = parse_pgvector(to_pgvector(vec))
    assert parsed == pytest.approx(vec)


def test_parse_empty():
    assert parse_pgvector("[]") == []


def test_cosine_identical():
    v = [1.0, 2.0, 3.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_opposite():
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_dim_mismatch():
    with pytest.raises(ValueError):
        cosine_similarity([1.0, 2.0], [1.0])
