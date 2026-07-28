# -*- coding: utf-8 -*-
"""build_dashboard_kurly.build_payload() 불변식 검증 (kurly/ 에서 pytest 실행)."""
import pytest

from build_dashboard_kurly import build_payload


@pytest.fixture(scope="module")
def payload():
    return build_payload()


def test_meta_counts(payload):
    assert payload["meta"]["n_products"] == 196
    assert payload["meta"]["n_reviews"] == 1550


def test_products_complete(payload):
    assert len(payload["products"]) == 196
    for p in payload["products"]:
        assert p["cat"] in ("165", "166", "169")
        assert p["brand"]                      # join 누락 없음 (사전 검증됨)
        assert 0 <= p["complaint_n"] <= p["review_n"]
        assert len(p["samples"]) >= 1          # 코딩된 리뷰가 1건 이상인 상품만 목록에 있음


def test_underwear_size_matches_report(payload):
    # 2026-07-28 스냅샷: 언더웨어·홈웨어(169) '작게 나옴' 22.5% (±3%p 허용)
    size = payload["cat_stats"]["169"]["size"]
    total = sum(size.values())
    assert abs(size.get("작게 나옴", 0) / total - 0.225) < 0.03


def test_brands_min_products(payload):
    assert all(b["n_products"] >= 3 for b in payload["brands"])
    assert 30 <= len(payload["brands"]) <= 40  # 2026-07-28 스냅샷 확인값 35 근방


def test_top_complaint_reason(payload):
    assert payload["complaint_reasons"][0][0].startswith("사이즈")
