# -*- coding: utf-8 -*-
"""
MD 인사이트 분석 스크립트 (4단계)

코드 부여된 리뷰 테이블(attributes_coded.csv)을 집계해
MD 관점 인사이트 차트 4개(PNG)와 집계 수치를 생성합니다.
API 호출 없음. 실행: python analyze_insights.py

산출물:
  report/charts/chart1_mention_rates.png   속성축별 언급률
  report/charts/chart2_size_risk.png       상품별 사이즈감 구성 (반품 리스크)
  report/charts/chart3_complaint_themes.png 불만 테마 분포 (평점대별)
  report/charts/chart4_subcategory.png     서브카테고리 × 속성 언급률 히트맵
  report/summary_stats.json                리포트 본문에 쓸 집계 수치
"""

import io
import json
import os
import re
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")  # 화면 없이 파일로만 저장
import matplotlib.pyplot as plt
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.path.dirname(__file__)
IN_PATH = os.path.join(BASE, "data", "attributes_coded.csv")
CHART_DIR = os.path.join(BASE, "report", "charts")
STATS_PATH = os.path.join(BASE, "report", "summary_stats.json")
os.makedirs(CHART_DIR, exist_ok=True)

# ── 차트 공통 스타일 (검증된 기본 팔레트) ──────────────────
INK = "#0b0b0b"        # 본문 텍스트
INK2 = "#52514e"       # 보조 텍스트
MUTED = "#898781"      # 축 레이블
GRID = "#e1e0d9"       # 그리드 헤어라인
BASELINE = "#c3c2b7"   # 축 베이스라인
SURFACE = "#fcfcfb"    # 차트 배경
BLUE = "#2a78d6"       # 기본 시리즈 (양/중립)
RED = "#e34948"        # 부정/리스크
GRAY_MID = "#d5d4cf"   # 다이버징 중립
BLUE_L = "#9ec5f4"     # 연한 파랑 (시퀀셜 밝은 단계)

plt.rcParams.update({
    "font.family": "Malgun Gothic",   # Windows 한글 폰트
    "axes.unicode_minus": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": INK,
    "axes.edgecolor": BASELINE,
    "xtick.color": MUTED,
    "ytick.color": INK2,
    "font.size": 11,
})


def style_axes(ax, keep="left"):
    """스파인은 베이스라인만 남기고 제거, 그리드는 헤어라인으로."""
    for side in ["top", "right", "bottom", "left"]:
        ax.spines[side].set_visible(side == keep)
    ax.tick_params(length=0)


# ── 데이터 로드 ────────────────────────────────────────────
df = pd.read_csv(IN_PATH, encoding="utf-8-sig")
N = len(df)
AXES = ["착용감", "핏", "촉감", "계절감", "사이즈감", "두께", "신축성", "비침", "기장"]
stats = {"리뷰수": N, "상품수": int(df["Product Name"].nunique())}

# ══════════════════════════════════════════════════════════
# 차트 1. 속성축별 언급률 — 리뷰가 실제로 말하는 것
# ══════════════════════════════════════════════════════════
mention = {a: int(df[a].notna().sum()) for a in AXES}
mention["불만점"] = int(df["불만점"].notna().sum())
order = sorted(mention, key=mention.get)

fig, ax = plt.subplots(figsize=(8, 4.6))
vals = [mention[a] for a in order]
# 불만점만 리스크 색, 나머지는 단일 파랑 (막대는 얇게, 값은 직접 표기)
colors = [RED if a == "불만점" else BLUE for a in order]
bars = ax.barh(order, vals, height=0.55, color=colors)
for b, v in zip(bars, vals):
    ax.text(v + 4, b.get_y() + b.get_height() / 2, f"{v}건 ({v/N:.0%})",
            va="center", fontsize=10, color=INK2)
ax.set_xlim(0, max(vals) * 1.22)
ax.set_title(f"리뷰 {N}건이 실제로 말하는 것 — 속성축별 언급 수", loc="left", fontsize=13, pad=12)
ax.xaxis.set_visible(False)
style_axes(ax, keep="left")
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "chart1_mention_rates.png"), dpi=150)
plt.close(fig)
stats["속성언급"] = mention

# ══════════════════════════════════════════════════════════
# 차트 2. 상품별 사이즈감 구성 — 반품 리스크 신호
# ══════════════════════════════════════════════════════════
sz = df[df["사이즈감"].notna()]
# 사이즈감 언급이 4건 이상인 상품만 (표본이 적으면 비율이 무의미)
prod_sz = sz.groupby("Product Name")["사이즈감"].value_counts().unstack(fill_value=0)
prod_sz = prod_sz[prod_sz.sum(axis=1) >= 4]
for c in ["작게 나옴", "정사이즈", "크게 나옴"]:
    if c not in prod_sz.columns:
        prod_sz[c] = 0
share = prod_sz.div(prod_sz.sum(axis=1), axis=0)
share = share.sort_values("작게 나옴")  # 작게 나옴 비율 높은 상품이 위로

fig, ax = plt.subplots(figsize=(9, 0.52 * len(share) + 1.8))
names = [n[:22] + "…" if len(n) > 22 else n for n in share.index]
left = pd.Series(0.0, index=share.index)
# 다이버징: 작게(빨강) / 정사이즈(중립 회색) / 크게(파랑), 조각 사이 2px 간격 효과는 흰 테두리로
for col, color in [("작게 나옴", RED), ("정사이즈", GRAY_MID), ("크게 나옴", BLUE)]:
    ax.barh(names, share[col], left=left.values, height=0.6, color=color,
            edgecolor=SURFACE, linewidth=1.5, label=col)
    left += share[col]
for i, (idx, row) in enumerate(share.iterrows()):
    if row["작게 나옴"] > 0:
        ax.text(row["작게 나옴"] / 2, i, f"{row['작게 나옴']:.0%}",
                va="center", ha="center", fontsize=9,
                color="white" if row["작게 나옴"] >= 0.18 else INK2)
n_total = prod_sz.sum(axis=1)
for i, idx in enumerate(share.index):
    ax.text(1.01, i, f"n={n_total[idx]}", va="center", fontsize=8.5, color=MUTED)
ax.set_xlim(0, 1.06)
ax.xaxis.set_visible(False)
ax.set_title("상품별 사이즈감 리뷰 구성 — '작게 나옴' 비율은 반품 리스크 신호", loc="left", fontsize=13, pad=12)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=3, frameon=False, fontsize=10)
style_axes(ax, keep="left")
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "chart2_size_risk.png"), dpi=150)
plt.close(fig)
stats["사이즈감_상품별"] = {
    idx: {"작게": float(share.loc[idx, "작게 나옴"]), "n": int(n_total[idx])} for idx in share.index
}

# ══════════════════════════════════════════════════════════
# 차트 3. 불만 테마 분포 — 평점만으로는 안 보이는 리스크
# ══════════════════════════════════════════════════════════
THEME_RULES = [  # (테마, 키워드 정규식) — 위에서부터 먼저 맞는 테마로 분류
    ("브라 기능(커버·지지력)", r"패드|와이어|어깨끈|끈|후크|받쳐|모아|들뜸|볼륨|밴드|가리개|새가슴|커버|뜨는|뜸|잡아주|누르|눌"),
    ("사이즈·핏 불만", r"작|크|사이즈|컵|둘레|맞지|타이트|헐렁|핏|밑위|폭"),
    ("마감·품질 불량", r"마감|봉제|박음질|불량|터짐|올이|실밥|검수|얼룩|택|로고|구멍|버클|약해|튼튼하지"),
    ("덥고 땀참", r"더움|더워|덥|땀|통풍|열|냉감"),
    ("세탁·내구성", r"내구|세탁|늘어|빠짐|이염|보풀|헤짐|빨래"),
    ("냄새", r"냄새"),
    ("색상·화면과 다름", r"색|화면|보정|비침|차콜|그레이|보일"),
    ("착용 불편", r"불편|까칠|쓸림|압박|갑갑|배김|끼임|조여|조였|조이|벗을 때"),
    ("가격·구성", r"가격|비싸|저렴|할인|빠진|이었으면"),
    ("디자인·취향", r"디자인|노골적|할머니|카라|자수|모양|취향"),
]


def theme_of(text: str) -> str:
    for theme, pat in THEME_RULES:
        if re.search(pat, str(text)):
            return theme
    return "기타"


comp = df[df["불만점"].notna()].copy()
comp["테마"] = comp["불만점"].map(theme_of)
comp["평점대"] = comp["Rating"].map(lambda r: "저평점(1~3점)" if r <= 3 else "고평점(4~5점)")
theme_tab = comp.groupby(["테마", "평점대"]).size().unstack(fill_value=0)
theme_tab = theme_tab.loc[theme_tab.sum(axis=1).sort_values().index]

fig, ax = plt.subplots(figsize=(8.5, 4.8))
y = range(len(theme_tab))
lo = theme_tab.get("저평점(1~3점)", pd.Series(0, index=theme_tab.index))
hi = theme_tab.get("고평점(4~5점)", pd.Series(0, index=theme_tab.index))
# 스택: 저평점(빨강) 위에 고평점(연파랑) — 고평점 속 불만이 '숨은 리스크'
ax.barh(y, lo, height=0.55, color=RED, label="저평점(1~3점) 리뷰")
ax.barh(y, hi, left=lo, height=0.55, color=BLUE_L, label="고평점(4~5점) 리뷰")
for i, t in enumerate(theme_tab.index):
    total = lo.iloc[i] + hi.iloc[i]
    ax.text(total + 0.5, i, f"{total}건", va="center", fontsize=10, color=INK2)
ax.set_yticks(list(y))
ax.set_yticklabels(theme_tab.index)
ax.set_xlim(0, (lo + hi).max() * 1.18)
ax.xaxis.set_visible(False)
ax.set_title(f"불만 {len(comp)}건의 테마 분포 — 고평점 리뷰에도 불만은 숨어 있다", loc="left", fontsize=13, pad=12)
ax.legend(loc="lower right", frameon=False, fontsize=10)
style_axes(ax, keep="left")
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "chart3_complaint_themes.png"), dpi=150)
plt.close(fig)
stats["불만테마"] = {t: {"저평점": int(lo[t]), "고평점": int(hi[t])} for t in theme_tab.index}
stats["불만_고평점_건수"] = int((comp["Rating"] >= 4).sum())
stats["불만_총건수"] = int(len(comp))

# ══════════════════════════════════════════════════════════
# 차트 4. 서브카테고리 × 속성 언급률 히트맵
# ══════════════════════════════════════════════════════════
def subcategory(name: str) -> str:
    n = str(name)
    if re.search(r"파자마|잠옷|홈웨어|라운지", n):
        return "잠옷/홈웨어"
    has_bra = "브라" in n
    has_bottom = re.search(r"팬티|드로즈|트렁크|비키니", n)
    if has_bra and has_bottom:
        return "브라·팬티 세트"
    if has_bra:
        return "브라"
    if has_bottom:
        return "팬티/드로즈"
    return "기타"


df["서브카테고리"] = df["Product Name"].map(subcategory)
sub_order = ["브라", "브라·팬티 세트", "팬티/드로즈", "잠옷/홈웨어"]
heat_axes = ["착용감", "핏", "사이즈감", "촉감", "계절감", "두께", "신축성", "불만점"]
heat = pd.DataFrame({
    sub: {a: df[df["서브카테고리"] == sub][a].notna().mean() for a in heat_axes}
    for sub in sub_order
}).T[heat_axes]

fig, ax = plt.subplots(figsize=(9, 3.4))
# 시퀀셜 단일 파랑 램프 (밝음=낮음, 어두움=높음)
im = ax.imshow(heat.values, cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
    "blue_seq", ["#f2f7fd", "#cde2fb", "#86b6ef", "#3987e5", "#184f95"]), aspect="auto", vmin=0)
ax.set_xticks(range(len(heat_axes)))
ax.set_xticklabels(heat_axes, fontsize=10.5)
ax.set_yticks(range(len(sub_order)))
counts = df["서브카테고리"].value_counts()
ax.set_yticklabels([f"{s} (n={counts.get(s, 0)})" for s in sub_order], fontsize=10.5)
for i in range(len(sub_order)):
    for j in range(len(heat_axes)):
        v = heat.values[i, j]
        ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=9.5,
                color="white" if v > 0.45 else INK2)
ax.set_title("서브카테고리별 속성 언급률 — 고객이 카테고리마다 묻는 질문이 다르다", loc="left", fontsize=13, pad=12)
ax.tick_params(length=0)
for side in ["top", "right", "bottom", "left"]:
    ax.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(CHART_DIR, "chart4_subcategory.png"), dpi=150)
plt.close(fig)
stats["서브카테고리_언급률"] = {s: {a: round(float(heat.loc[s, a]), 3) for a in heat_axes} for s in sub_order}

# ── 추가 집계: 리포트 본문용 수치 ──────────────────────────
# 착용상황 분포 (상세페이지에 없는 구매 맥락)
ctx = Counter()
for x in df["착용상황"].dropna():
    try:
        for v in json.loads(str(x).replace("'", '"')):
            ctx[v] += 1
    except (json.JSONDecodeError, TypeError):
        pass
stats["착용상황_TOP"] = dict(ctx.most_common(15))

# 상품명에 이미 드러난 속성 vs 리뷰에서만 나오는 속성
name_blob = " ".join(df["Product Name"].unique())
stats["상품명_키워드"] = {
    "쿨/시원(계절감)": len(re.findall(r"쿨|시원|아이스|에어리", name_blob)),
    "심리스/노와이어(구조)": len(re.findall(r"심리스|노와이어|와이어리스|노라인", name_blob)),
}

# 저평점 리뷰에서 사이즈감 언급 비율 vs 고평점
low, high = df[df["Rating"] <= 3], df[df["Rating"] >= 4]
stats["사이즈감_언급률"] = {"저평점": round(float(low["사이즈감"].notna().mean()), 3),
                          "고평점": round(float(high["사이즈감"].notna().mean()), 3)}
stats["불만점_언급률"] = {"저평점": round(float(low["불만점"].notna().mean()), 3),
                        "고평점": round(float(high["불만점"].notna().mean()), 3)}

with open(STATS_PATH, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print("차트 4개 저장 완료 →", CHART_DIR)
print("집계 수치 저장 →", STATS_PATH)
print("\n주요 수치 미리보기:")
print("- 불만 언급:", stats["불만_총건수"], "건 중 고평점 리뷰 발생", stats["불만_고평점_건수"], "건")
print("- 사이즈감 언급률: 저평점", stats["사이즈감_언급률"]["저평점"], "vs 고평점", stats["사이즈감_언급률"]["고평점"])
print("- 착용상황 TOP:", list(stats["착용상황_TOP"].items())[:8])
