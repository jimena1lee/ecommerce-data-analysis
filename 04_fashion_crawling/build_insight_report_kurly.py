# -*- coding: utf-8 -*-
"""
MD 인사이트 리포트 생성 (4단계, 가장 중요한 단계)

지금까지 만든 속성 코드북 + 상품별 Semantic ID를 근거로,
'상세페이지(판매자 언어)에는 없지만 리뷰(고객 언어)에서 드러나는 정보'를
차트 4개 + markdown 리포트로 정리한다. API 호출 없음 — 전부 로컬 집계.

산출물:
- report/chart1_attribute_mentions.png : 리뷰에서 가장 많이 언급된 실착 속성 축 TOP
- report/chart2_size_by_category.png   : 카테고리별 사이즈감 분포
- report/chart3_complaint_types.png    : 불만사유 유형 TOP 10
- report/chart4_risk_products.png      : 불만비율 높은 상품 TOP 10 (반품 리스크 후보)
- report/insight_report_kurly.md       : 위 차트를 근거로 쓴 MD용 인사이트 리포트
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

DATA_DIR = "data"
REPORT_DIR = "report"

CODED_PATH = os.path.join(DATA_DIR, "kurly_attributes_coded.csv")
PRODUCT_PATH = os.path.join(DATA_DIR, "kurly_product_semantic_ids.csv")

CATEGORY_NAMES = {165: "패션의류", 166: "신발·잡화", 169: "언더웨어·홈웨어"}
AXES = ["핏", "사이즈감", "기장", "비침", "두께", "신축성", "착용상황", "계절감"]

# 기존 노트북들과 동일한 팔레트/폰트 설정을 재사용 (일관된 톤 유지)
BLUE, RED = "#2a78d6", "#e34948"
INK, SECONDARY, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SURFACE = "#fcfcfb"

_available = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR")
             if f in _available), "DejaVu Sans")

plt.rcParams.update({
    "font.family": FONT,
    "axes.unicode_minus": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": "#c3c2b7",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": False, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "text.color": INK, "axes.labelcolor": SECONDARY,
    "xtick.color": MUTED, "ytick.color": MUTED,
})


# 불만사유는 LLM이 자유 문장으로 적어서 표현이 갈린다 (예: "사이즈가 작음" vs "사이즈 작음").
# 리포트에서 의미 있는 집계가 되도록 키워드 기반으로 유형을 묶는다.
COMPLAINT_KEYWORDS = [
    ("사이즈 작음", ["작"]),
    ("사이즈/기장 큼", ["큼", "크게"]),
    ("배송 지연", ["배송"]),
    ("기장 짧음", ["기장", "짧"]),
    ("비침 있음", ["비침"]),
    ("색상 불만족", ["색상", "색깔"]),
    ("마감/봉제 불량", ["실밥", "봉제", "마감", "박음질"]),
    ("세탁 후 변형", ["수축", "변형", "세탁"]),
    ("소재/촉감 불만", ["촉감", "까슬", "답답", "무거움"]),
    ("디자인/핏 불만", ["디자인", "핏 불량", "싼티", "촌스러", "부해", "핏과"]),
    ("가격 대비 품질", ["가격", "품질"]),
    ("더움/불편", ["더움", "더워"]),
    ("말림/들뜸", ["말림", "말려", "들뜸"]),
]


def group_complaint(text: str) -> str:
    for label, keywords in COMPLAINT_KEYWORDS:
        if any(k in text for k in keywords):
            return label
    return "기타"


def chart1_attribute_mentions(df: pd.DataFrame):
    """상세페이지 문구가 아니라 '고객이 실제로 언급한' 속성 축이 무엇인지 보여준다."""
    counts = {axis: df[axis].notna().sum() for axis in AXES}
    s = pd.Series(counts).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(s.index, s.values, color=BLUE)
    for i, v in enumerate(s.values):
        ax.text(v + 5, i, f"{v}건 ({v * 100 // len(df)}%)", va="center", fontsize=9, color=SECONDARY)
    ax.set_xlabel("리뷰에서 해당 속성이 언급된 건수")
    ax.set_title("리뷰에서 가장 많이 언급된 실착 속성 축 (전체 1,543건 중)", loc="left", fontsize=12, pad=12)
    plt.tight_layout()
    path = os.path.join(REPORT_DIR, "chart1_attribute_mentions.png")
    plt.savefig(path, dpi=140)
    plt.close(fig)
    return path, s


def chart2_size_by_category(df: pd.DataFrame):
    """카테고리마다 '크게/작게/정사이즈' 언급 비율이 다른지 비교한다."""
    ct = pd.crosstab(df["category"], df["사이즈감"], normalize="index") * 100
    ct = ct.reindex(columns=["크게 나옴", "정사이즈", "작게 나옴"]).fillna(0)
    ct.index = [CATEGORY_NAMES[c] for c in ct.index]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = {"크게 나옴": "#8fb8e8", "정사이즈": BLUE, "작게 나옴": RED}
    x = range(len(ct))
    bottom = [0] * len(ct)
    for col in ct.columns:
        ax.bar(x, ct[col], bottom=bottom, label=col, color=colors[col], width=0.5)
        bottom = [b + v for b, v in zip(bottom, ct[col])]
    ax.set_xticks(list(x))
    ax.set_xticklabels(ct.index)
    ax.set_ylabel("사이즈감 언급 중 비율 (%)")
    ax.set_title("카테고리별 사이즈감 언급 분포", loc="left", fontsize=12, pad=12)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    plt.tight_layout()
    path = os.path.join(REPORT_DIR, "chart2_size_by_category.png")
    plt.savefig(path, dpi=140)
    plt.close(fig)
    return path, ct


def chart3_complaint_types(df: pd.DataFrame):
    """불만사유를 유형별로 묶어서 어떤 문제가 가장 반복되는지 본다."""
    reasons = df["불만사유"].dropna()
    grouped = reasons.map(group_complaint).value_counts().head(10).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(grouped.index, grouped.values, color=RED)
    for i, v in enumerate(grouped.values):
        ax.text(v + 0.3, i, str(v), va="center", fontsize=9, color=SECONDARY)
    ax.set_xlabel("건수")
    ax.set_title(f"불만사유 유형 TOP 10 (불만사유 언급 총 {len(reasons)}건 중)", loc="left", fontsize=12, pad=12)
    plt.tight_layout()
    path = os.path.join(REPORT_DIR, "chart3_complaint_types.png")
    plt.savefig(path, dpi=140)
    plt.close(fig)
    return path, grouped


def chart4_risk_products(products: pd.DataFrame):
    """리뷰 5건 이상 상품 중 불만비율이 높은 상품 = 반품/CS 리스크 후보."""
    risky = products[products["리뷰수"] >= 5].sort_values("불만비율", ascending=False).head(10)
    risky = risky.iloc[::-1]  # barh는 아래부터 그려지므로 순서 뒤집기

    fig, ax = plt.subplots(figsize=(8, 5))
    labels = [n[:24] + ("…" if len(n) > 24 else "") for n in risky["Product Name"]]
    ax.barh(labels, risky["불만비율"] * 100, color=RED)
    for i, (v, n) in enumerate(zip(risky["불만비율"] * 100, risky["리뷰수"])):
        ax.text(v + 1, i, f"{v:.0f}% (리뷰{n}건)", va="center", fontsize=8.5, color=SECONDARY)
    ax.set_xlabel("불만비율 (%)")
    ax.set_title("불만비율 TOP 10 상품 — 반품/CS 리스크 후보 (리뷰 5건 이상)", loc="left", fontsize=12, pad=12)
    plt.tight_layout()
    path = os.path.join(REPORT_DIR, "chart4_risk_products.png")
    plt.savefig(path, dpi=140)
    plt.close(fig)
    return path, risky


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    df = pd.read_csv(CODED_PATH)
    products = pd.read_csv(PRODUCT_PATH)

    p1, mentions = chart1_attribute_mentions(df)
    p2, size_ct = chart2_size_by_category(df)
    p3, complaints = chart3_complaint_types(df)
    p4, risky = chart4_risk_products(products)

    # 히든 불만 비율: 감성 태그는 만족/중립인데 불만사유가 같이 달린 리뷰
    hidden = df[df["불만사유"].notna() & df["감성"].isin(["만족", "중립"])]
    total_complaints = df["불만사유"].notna().sum()

    top_axis, top_axis_n = mentions.index[-1], mentions.iloc[-1]
    # '기타'는 정보성이 없으므로, 서술에는 그 다음으로 큰 유형을 사용
    named = complaints.drop("기타", errors="ignore")
    top_complaint, top_complaint_n = named.index[-1], named.iloc[-1]

    report = f"""# 컬리 패션·잡화 리뷰 마이닝 인사이트 리포트

- 데이터: 컬리 패션의류(165)·신발잡화(166)·언더웨어홈웨어(169) 3개 카테고리, 상품 199개, 리뷰 1,543건
- 방법: Gemini({', '.join(AXES)} 등 8축) 실착 속성 추출 → 코드북 정규화 → 상품별 Semantic ID 부여
- 주의: 컬리 리뷰에는 별점이 없어, '감성(만족/불만/중립)' 태그를 별점 대신 리스크 지표로 사용

## 1. 상세페이지엔 없지만 리뷰에서 드러나는 정보

![리뷰 속성 언급 빈도](chart1_attribute_mentions.png)

상품 상세페이지는 '판매자의 언어'로 소재·사이즈표를 나열하지만, 고객이 리뷰에서
실제로 가장 많이 언급하는 축은 **'{top_axis}'**({top_axis_n}건, 전체의 {top_axis_n*100//len(df)}%)입니다.
계절감·착용상황처럼 상세페이지 상단에 아이콘 한두 개로 뭉뚱그려지는 정보가,
실제로는 구매 결정에 이만큼 자주 오가는 화두라는 뜻입니다.

## 2. 카테고리별 사이즈감 — "이 카테고리는 크게 사야 하나요?"

![카테고리별 사이즈감](chart2_size_by_category.png)

| 카테고리 | 크게 나옴 | 정사이즈 | 작게 나옴 |
|---|---|---|---|
{chr(10).join(f"| {idx} | {row['크게 나옴']:.0f}% | {row['정사이즈']:.0f}% | {row['작게 나옴']:.0f}% |" for idx, row in size_ct.iterrows())}

언더웨어·홈웨어(169)는 '작게 나옴' 언급이 다른 카테고리보다 뚜렷하게 높습니다.
이 카테고리는 상세페이지 사이즈표 옆에 "실측보다 타이트하게 나오는 편"과 같은
안내 문구를 추가하면 반품·교환 문의를 줄일 수 있는 후보입니다.

## 3. 반복되는 불만 유형

![불만사유 유형](chart3_complaint_types.png)

불만사유가 확인된 리뷰 {total_complaints}건 중 뚜렷하게 유형화되는 것 중 가장 빈번한 것은
**'{top_complaint}'**({top_complaint_n}건)입니다. 나머지는 상품마다 제각각인
롱테일 불만("때 탐", "말려올라감", "디자인 촌스러움" 등)이라 하나의 유형으로
묶이지 않는데, 이는 반대로 **정형화된 리뷰 요약이나 별점만으로는 절대 잡히지 않는
디테일**이라는 뜻이기도 합니다. 흥미로운 점은, 불만사유가 달린 리뷰 중
**{len(hidden)}건({len(hidden)*100//total_complaints if total_complaints else 0}%)은 리뷰의 전체 톤이
'만족' 또는 '중립'으로 분류됐다는 것**입니다. 즉 별점(컬리는 별점 자체가 없음)이나
감성만으로 리뷰를 필터링하면, 좋은 평가 속에 숨어 있는 불만 신호를
그대로 놓치게 됩니다. — 리뷰 전문을 읽거나 텍스트 마이닝을 해야만 잡히는 시그널입니다.

## 4. 반품·CS 리스크 후보 상품

![불만비율 TOP 10](chart4_risk_products.png)

| 상품명 | 리뷰수 | 불만비율 | Semantic ID |
|---|---|---|---|
{chr(10).join(f"| {n[:30]} | {r} | {b:.0%} | `{s}` |" for n, r, b, s in zip(risky['Product Name'].iloc[::-1], risky['리뷰수'].iloc[::-1], risky['불만비율'].iloc[::-1], risky['semantic_id'].iloc[::-1]))}

이 목록은 '평점이 낮은 상품' 목록이 아니라(컬리는 별점이 없어 산출 불가),
**리뷰 문장에서 불만이 직접 언급된 비율**로 뽑은 것이 핵심 차별점입니다.
같은 리뷰수 대비 불만비율이 높은 상품은 상품기획(MD) 관점에서
1) 상세페이지 정보 보강, 2) 사이즈 가이드 재검토, 3) 우선 CS 대응 대상으로
선별해 볼 수 있습니다.

## 5. 결론 — Semantic ID의 활용 가능성

리뷰에서 뽑은 속성 코드(예: `사2-두1-신1-착1-계1`)는 상세페이지 텍스트 없이도
"이 상품은 사이즈가 크게 나오고, 얇고 신축성 좋은 원단이며, 데일리로 여름에 입는다"는
요약을 자동으로 만들어줍니다. 신규 입고 상품처럼 리뷰가 아직 없는
콜드스타트 상품에도, 같은 코드북을 공유하는 유사 상품의 Semantic ID를
참고해 추천·MD 태깅에 활용할 수 있습니다.
"""

    out_path = os.path.join(REPORT_DIR, "insight_report_kurly.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"차트 4개 저장: {p1}, {p2}, {p3}, {p4}")
    print(f"리포트 저장: {out_path}")


if __name__ == "__main__":
    main()
