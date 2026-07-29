# -*- coding: utf-8 -*-
"""build_payload() 불변식 검증 (kurly_kidswear/ 에서 pytest 실행)."""
import pytest

from build_kidswear_dashboard import build_payload


@pytest.fixture(scope="module")
def payload():
    return build_payload()


def test_meta(payload):
    m = payload["meta"]
    assert m["n_sku"] == 3640
    assert m["n_reviews"] == 2498
    assert m["n_brands"] == 47
    assert m["top1pct_share"] == 53.3


def test_price_delivery_cells(payload):
    """2×2 히트맵은 네 칸이 모두 있어야 하고 단조 증가해야 한다."""
    cells = payload["price_delivery"]
    assert len(cells) == 4
    by_key = {(c["price"], c["delivery"]): c for c in cells}
    assert by_key[("2만원 미만", "샛별배송")]["density"] == 33.00
    assert by_key[("2만원 이상", "샛별배송")]["density"] == 4.41
    assert by_key[("2만원 미만", "판매자배송")]["density"] == 0.86
    assert by_key[("2만원 이상", "판매자배송")]["density"] == 0.24
    ordered = sorted(cells, key=lambda c: -c["density"])
    assert [c["density"] for c in ordered] == [33.00, 4.41, 0.86, 0.24]


def test_dawn_lift_derived(payload):
    """샛별 전환 시 리뷰밀도 배율 — 2막 슬로프 차트의 입력."""
    lift = {d["item"]: d for d in payload["derived"]["dawn_lift"]}
    assert set(lift) == {"실내화", "학용품"}
    assert lift["실내화"]["seller_density"] == 2.93
    assert lift["실내화"]["dawn_density"] == 75.43
    assert round(lift["실내화"]["multiple"]) == 26
    assert lift["학용품"]["seller_density"] == 0.90
    assert lift["학용품"]["dawn_density"] == 27.55
    assert round(lift["학용품"]["multiple"]) == 31


def test_proposal1_candidates(payload):
    """샛별 0개 + 판매자 리뷰밀도 상위 = 확대 후보."""
    c = payload["derived"]["proposal1"]
    assert [x["item"] for x in c] == ["잠옷", "장화", "샌들"]
    assert all(x["dawn_sku"] == 0 for x in c)
    # 69/40=1.725 는 정확한 tie 지점이라 round-half-even 규칙상 1.72 로
    # 내림된다 (category_delivery.csv, category.csv, 분석리포트 모두 1.72).
    assert c[0]["seller_density"] == 1.72


def test_seasonal_derived(payload):
    s = payload["derived"]["seasonal"]
    assert s["total_sku"] == 1036
    assert s["total_reviews"] == 293
    assert s["sku_share"] == 28.5
    assert s["review_share"] == 11.7
    assert [r["item"] for r in s["rows"]] == ["한복", "파티·이벤트용품", "아우터", "수영"]


def test_no_uncorrected_values(payload):
    """보정 전 오류값이 payload 에 섞이지 않았는지 확인."""
    cd = {c["item"]: c for c in payload["category_delivery"]}
    assert cd["학용품"]["seller_reviews"] == 9      # 보정 전 오류값은 0
    assert cd["하의"]["dawn_reviews"] == 21         # 보정 전 오류값은 0
    brands = {b["brand"]: b for b in payload["brand"]}
    assert brands["하우키즈풀"]["reviews"] == 661
    bd = {b["brand"]: b for b in payload["brand_delivery"]}
    assert bd["하우키즈풀"]["seller_reviews"] == 79   # 보정 전 오류값은 0
