# -*- coding: utf-8 -*-
"""data/*.csv 가 분석 리포트와 일치하는지 검증 (kurly_kidswear/ 에서 pytest 실행).

여기 박힌 기대값은 2026-07-28 스냅샷 기준이다. 데이터를 다시 수집하면
값이 바뀌므로 테스트도 함께 갱신해야 한다.
"""
import os

import pandas as pd
import pytest

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def read(name, index_col=0):
    return pd.read_csv(os.path.join(DATA, name), encoding="utf-8-sig",
                       index_col=index_col)


@pytest.fixture(scope="module")
def meta():
    return read("meta.csv", index_col=None).iloc[0]


def test_meta_matches_report(meta):
    assert meta["n_sku"] == 3640
    assert meta["n_reviews"] == 2498          # 보정 후. 1,420 이면 보정 누락이다
    assert meta["n_brands"] == 47
    assert meta["n_reviewed_sku"] == 599
    assert meta["n_zero_sku"] == 3041
    assert round(float(meta["gini"]), 3) == 0.944


def test_pareto_matches_report():
    p = read("pareto.csv")
    assert p.loc["1%", "SKU수"] == 36         # int(round(36.4)) — ceil 이면 37 이 된다
    assert p.loc["1%", "누적리뷰"] == 1332
    assert p.loc["1%", "리뷰점유율%"] == 53.3
    assert p.loc["5%", "리뷰점유율%"] == 80.2
    assert p.loc["10%", "리뷰점유율%"] == 90.6
    assert p.loc["20%", "리뷰점유율%"] == 100.0


def test_delivery_matches_report():
    d = read("delivery.csv")
    assert d.loc["샛별배송", "SKU수"] == 81
    assert d.loc["샛별배송", "총리뷰수"] == 1272
    assert d.loc["샛별배송", "리뷰per_SKU"] == 15.70
    assert d.loc["샛별배송", "리뷰0_비율%"] == 28.4
    assert d.loc["판매자배송", "SKU수"] == 3559
    assert d.loc["판매자배송", "총리뷰수"] == 1226
    assert d.loc["판매자배송", "리뷰per_SKU"] == 0.34
    assert d.loc["판매자배송", "리뷰0_비율%"] == 84.8


def test_price_delivery_2x2():
    """센터피스 히트맵. 단조 증가하며 역전이 없어야 한다."""
    x = read("price_delivery.csv")
    assert x.loc["2만원 미만", "SKU_샛별배송"] == 32
    assert x.loc["2만원 미만", "리뷰_샛별배송"] == 1056
    assert x.loc["2만원 미만", "밀도_샛별배송"] == 33.00
    assert x.loc["2만원 미만", "밀도_판매자배송"] == 0.86
    assert x.loc["2만원 이상", "밀도_샛별배송"] == 4.41
    assert x.loc["2만원 이상", "밀도_판매자배송"] == 0.24
    assert (x.loc["2만원 미만", "밀도_샛별배송"] > x.loc["2만원 이상", "밀도_샛별배송"]
            > x.loc["2만원 미만", "밀도_판매자배송"] > x.loc["2만원 이상", "밀도_판매자배송"])


def test_category_delivery_natural_experiment():
    """같은 품목 안에서 배송타입만 다른 쌍 — 2막의 핵심 근거."""
    x = read("category_delivery.csv")
    assert x.loc["실내화", "SKU_샛별배송"] == 7
    assert x.loc["실내화", "리뷰_샛별배송"] == 528
    assert x.loc["실내화", "SKU_판매자배송"] == 28
    assert x.loc["실내화", "리뷰_판매자배송"] == 82
    assert x.loc["학용품", "SKU_샛별배송"] == 11
    assert x.loc["학용품", "리뷰_샛별배송"] == 303
    assert x.loc["학용품", "SKU_판매자배송"] == 10
    assert x.loc["학용품", "리뷰_판매자배송"] == 9      # 0 이 아니다 (보정 전 오류값)


def test_proposal1_candidates_have_no_dawn_sku():
    """제안 ①의 후보 3품목은 샛별 SKU 가 0 이면서 판매자 리뷰밀도가 상위여야 한다."""
    x = read("category_delivery.csv")
    # 잠옷은 69/40 = 1.725 로 정확한 동점이고, pandas 는 round-half-even 이라
    # 1.72 가 된다(리포트도 1.72). 장화 38/22 = 1.727... 은 1.73.
    for item, density in (("잠옷", 1.72), ("장화", 1.73), ("샌들", 0.84)):
        assert x.loc[item, "SKU_샛별배송"] == 0
        assert x.loc[item, "밀도_판매자배송"] == density
    for item in ("상의", "하의", "아우터"):
        assert x.loc[item, "밀도_판매자배송"] < 0.2


def test_brand_delivery_natural_experiment():
    """하우키즈풀 — 같은 브랜드 안에서 배송타입만 다른 사례."""
    b = read("brand_delivery.csv")
    h = b.loc["하우키즈풀"]
    assert h["SKU_샛별배송"] == 27
    assert h["리뷰_샛별배송"] == 582
    assert h["밀도_샛별배송"] == 21.56
    assert h["SKU_판매자배송"] == 93
    assert h["리뷰_판매자배송"] == 79      # 0 이 아니다 (보정 전 오류값)
    assert h["밀도_판매자배송"] == 0.85
    assert h["평균가_샛별배송"] == 12962
    assert h["평균가_판매자배송"] == 33770


def test_brand_totals_reconcile():
    """brand.csv 총리뷰 = brand_delivery.csv 샛별 + 판매자."""
    br = read("brand.csv")
    bd = read("brand_delivery.csv")
    for name in bd.index:
        assert br.loc[name, "총리뷰수"] == (bd.loc[name, "리뷰_샛별배송"]
                                          + bd.loc[name, "리뷰_판매자배송"])


def test_seasonal_items_for_proposal2():
    """제안 ②의 시즌 상품군 — 합계 1,036 SKU / 293 리뷰."""
    e = read("category_etc.csv")
    c = read("category.csv")
    assert e.loc["한복", "SKU수"] == 413
    assert e.loc["한복", "총리뷰수"] == 152
    assert e.loc["파티·이벤트용품", "SKU수"] == 333
    assert e.loc["수영", "SKU수"] == 47
    assert c.loc["아우터", "SKU수"] == 243
    total_sku = (e.loc["한복", "SKU수"] + e.loc["파티·이벤트용품", "SKU수"]
                 + e.loc["수영", "SKU수"] + c.loc["아우터", "SKU수"])
    assert total_sku == 1036


def test_category_totals_reconcile():
    """품목별 총리뷰 = 샛별 + 판매자. 두 CSV 가 서로 어긋나지 않아야 한다."""
    c = read("category.csv")
    x = read("category_delivery.csv")
    for item in c.index:
        assert c.loc[item, "총리뷰수"] == (x.loc[item, "리뷰_샛별배송"]
                                          + x.loc[item, "리뷰_판매자배송"])
