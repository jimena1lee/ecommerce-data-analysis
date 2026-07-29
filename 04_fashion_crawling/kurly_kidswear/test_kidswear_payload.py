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


from svg_charts import heatmap_2x2, mirror_bars, pareto_curve, slope


def test_pareto_curve_renders_all_points(payload):
    svg = pareto_curve(payload["pareto"][:4])       # 50% 구간은 그리지 않는다
    assert svg.startswith("<svg")
    assert svg.count("<circle") == 4
    for label in ("1%", "5%", "10%", "20%"):
        assert f">{label}<" in svg


def test_heatmap_has_four_cells_with_values(payload):
    svg = heatmap_2x2(payload["price_delivery"])
    assert svg.count("<rect") == 8      # 칸마다 배경 + 테두리 2개
    for v in ("33.0", "4.41", "0.86", "0.24"):
        assert v in svg


def test_slope_shows_both_items(payload):
    svg = slope(payload["derived"]["dawn_lift"])
    assert "실내화" in svg and "학용품" in svg
    assert "26" in svg and "31" in svg          # 배율 라벨


def test_mirror_bars_covers_all_categories(payload):
    svg = mirror_bars(payload["category"])
    for item in ("상의", "하의", "아우터", "실내화", "학용품"):
        assert item in svg


def test_charts_have_no_hardcoded_colors(payload):
    """색은 CSS 변수로만 참조해야 다크모드에서 깨지지 않는다.

    '#' 전체를 금지하면 html.escape 가 만드는 &#x27; 같은 엔티티에 오탐이 난다.
    hex 색상 리터럴만 잡는다.
    """
    import re
    hex_color = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    svgs = {"pareto": pareto_curve(payload["pareto"][:4]),
            "heatmap": heatmap_2x2(payload["price_delivery"]),
            "slope": slope(payload["derived"]["dawn_lift"]),
            "mirror": mirror_bars(payload["category"])}
    for name, svg in svgs.items():
        found = hex_color.findall(svg)
        assert not found, f"{name} 에 hex 색상 {found} — 다크모드에서 대비가 깨진다"


def test_chart_functions_survive_degenerate_input():
    """행이 1개(파레토) 이거나 0개(나머지) 여도 예외 없이 유효한 SVG 를 반환해야 한다."""
    assert pareto_curve([{"label": "1%", "sku": 36, "share": 53.3}]).startswith("<svg")
    assert mirror_bars([]).startswith("<svg")
    assert heatmap_2x2([]).startswith("<svg")
    assert slope([]).startswith("<svg")
