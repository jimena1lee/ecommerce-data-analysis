# -*- coding: utf-8 -*-
"""build_dashboard_kurly.build_payload() 불변식 검증 (kurly/ 에서 pytest 실행)."""
import pytest

from build_dashboard_kurly import build_payload


@pytest.fixture(scope="module")
def payload():
    return build_payload()


def test_meta_counts(payload):
    assert payload["meta"]["n_products"] == 199
    assert payload["meta"]["n_reviews"] == 1543


def test_products_complete(payload):
    assert len(payload["products"]) == 199
    for p in payload["products"]:
        assert p["cat"] in ("165", "166", "169")
        assert p["brand"]                      # join 누락 없음 (사전 검증됨)
        assert 0 <= p["complaint_n"] <= p["review_n"]
        assert len(p["samples"]) >= 1          # 코딩된 리뷰가 1건 이상인 상품만 목록에 있음


def test_underwear_size_matches_report(payload):
    # 기존 리포트: 언더웨어·홈웨어(169) '작게 나옴' 27% (±3%p 허용)
    size = payload["cat_stats"]["169"]["size"]
    total = sum(size.values())
    assert abs(size.get("작게 나옴", 0) / total - 0.27) < 0.03


def test_brands_min_products(payload):
    assert all(b["n_products"] >= 3 for b in payload["brands"])
    assert 25 <= len(payload["brands"]) <= 33  # 사전 확인값 29 근방


def test_top_complaint_reason(payload):
    assert payload["complaint_reasons"][0][0].startswith("사이즈")
