# -*- coding: utf-8 -*-
"""컬리 × 무신사 통합 포트폴리오(output/portfolio.html) 재생성 빌더.

kurly/data · musinsa/data의 최신 수집본(상품·리뷰)에서 통계를 계산하고
matplotlib 차트 12종을 base64로 인라인 임베드한 자기완결 정적 HTML을 만든다.
분석·차트 로직은 각 채널 analysis 노트북(analysis.ipynb / analysis_kurly_*.ipynb)과
동일하다. 색/폰트/레이아웃은 기존 포트폴리오 디자인 시스템을 그대로 재사용한다.

실행:  cd 04_fashion_crawling && python build_portfolio_combined.py
산출물: output/portfolio.html
"""

import base64
import io
import json
import re
from collections import Counter
from glob import glob

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

# ── 팔레트 (기존 디자인 시스템) ─────────────────────────────
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

KURLY_DIR = "kurly/data"
MUSINSA_DIR = "musinsa/data"
OUT_PATH = "output/portfolio.html"
COLLECT_DATE = "2026-07-28"


def png_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ── 데이터 로딩 ────────────────────────────────────────────
def load_kurly(cat: str) -> pd.DataFrame:
    with open(sorted(glob(f"{KURLY_DIR}/kurly_products_{cat}_*.json"))[-1], encoding="utf-8") as f:
        prod = pd.DataFrame(json.load(f)).drop(columns=["_goods_no"])
    prod["가격"] = pd.to_numeric(prod["Price"].str.replace(",", ""), errors="coerce")
    prod = prod.dropna(subset=["가격"]).astype({"가격": int})
    prod["할인율"] = pd.to_numeric(prod["Discount Rate"].str.rstrip("%"), errors="coerce").fillna(0).astype(int)
    prod["리뷰수상한"] = prod["Review Count"].str.endswith("+")
    prod["리뷰수"] = prod["Review Count"].str.replace(",", "").str.rstrip("+").astype(int)
    prod["브랜드"] = prod["Brand"].replace("", "(미표기)")
    prod["_name"] = prod["Category"].iloc[0]
    return prod


def load_musinsa():
    with open(sorted(glob(f"{MUSINSA_DIR}/products_026_*.json"))[-1], encoding="utf-8") as f:
        prod = pd.DataFrame(json.load(f)).drop(columns=["_goods_no"])
    with open(sorted(glob(f"{MUSINSA_DIR}/reviews_026_*.json"))[-1], encoding="utf-8") as f:
        rev = pd.DataFrame(json.load(f))
    prod["가격"] = prod["Price"].str.replace(",", "").astype(int)
    prod["할인율"] = prod["Discount Rate"].str.rstrip("%").astype(int)
    prod["리뷰수"] = prod["Review Count"].str.replace(",", "").astype(int)
    prod["평점"] = pd.to_numeric(prod["Rating"], errors="coerce")
    rev["평점"] = pd.to_numeric(rev["Rating"])
    return prod, rev


k169 = load_kurly("169")
k166 = load_kurly("166")
m_prod, m_rev = load_musinsa()

S = {}  # 모든 통계를 담는 dict (프로즈·표에 주입)


# ── 컬리 169 통계 ──────────────────────────────────────────
S["k169_n"] = len(k169)
S["k169_med"] = int(k169["가격"].median())
S["k169_list0"] = int((k169["할인율"] == 0).sum())
S["k169_disc_med"] = int(k169["할인율"].median())
S["k169_disc_max"] = int(k169["할인율"].max())
S["k169_25plus"] = round((k169["할인율"] >= 25).mean() * 100)
S["k169_rev0"] = int((k169["리뷰수"] == 0).sum())
S["k169_cap"] = int(k169["리뷰수상한"].sum())
_k169_named = k169[k169["브랜드"] != "(미표기)"]["브랜드"].value_counts()
S["k169_brand_top"] = _k169_named.index[0]
S["k169_brand_top_n"] = int(_k169_named.iloc[0])
S["k169_brand2"] = _k169_named.index[1]
S["k169_brand2_n"] = int(_k169_named.iloc[1])
S["k169_brand1cnt"] = int((_k169_named == 1).sum())
# 상위 10% 리뷰 점유율
_s = k169["리뷰수"].sort_values(ascending=False).reset_index(drop=True)
_share = _s.cumsum() / _s.sum() * 100
S["k169_top10share"] = round(_share.iloc[max(0, int(len(_s) * 0.1) - 1)])

# ── 컬리 166 통계 ──────────────────────────────────────────
S["k166_n"] = len(k166)
S["k166_med"] = int(k166["가격"].median())
S["k166_list0"] = int((k166["할인율"] == 0).sum())
S["k166_list0_pct"] = round((k166["할인율"] == 0).mean() * 100)
S["k166_disc_med"] = int(k166["할인율"].median())
S["k166_25plus"] = round((k166["할인율"] >= 25).mean() * 100)
S["k166_rev0"] = int((k166["리뷰수"] == 0).sum())
S["k166_rev0_pct"] = round((k166["리뷰수"] == 0).mean() * 100)
_s6 = k166["리뷰수"].sort_values(ascending=False).reset_index(drop=True)
_share6 = _s6.cumsum() / _s6.sum() * 100
S["k166_top10share"] = round(_share6.iloc[max(0, int(len(_s6) * 0.1) - 1)])
S["k166_over_k169"] = round(S["k166_med"] / S["k169_med"])

# ── 무신사 026 통계 ────────────────────────────────────────
S["m_n"] = len(m_prod)
S["m_med"] = int(m_prod["가격"].median())
S["m_min"] = int(m_prod["가격"].min())
S["m_max"] = int(m_prod["가격"].max())
S["m_mean"] = int(round(m_prod["가격"].mean()))
S["m_list0"] = int((m_prod["할인율"] == 0).sum())
S["m_list0_pct"] = round((m_prod["할인율"] == 0).mean() * 100, 1)
S["m_disc_med"] = int(m_prod["할인율"].median())
S["m_disc_max"] = int(m_prod["할인율"].max())
S["m_25plus"] = round((m_prod["할인율"] >= 25).mean() * 100)
_m_brand = m_prod["Brand"].value_counts()
_m_top = _m_brand[_m_brand >= 2].sort_values(ascending=False)
S["m_brand_top"] = _m_top.index[0]
S["m_brand_top_n"] = int(_m_top.iloc[0])
S["m_brand_next"] = [f"{b}({int(n)}개)" for b, n in _m_top.iloc[1:4].items()]
S["m_brand1cnt"] = int((_m_brand == 1).sum())
# 리뷰수 top 2 (scatter 주석 · 판매볼륨)
_pr = m_prod[m_prod["평점"] > 0]
_top2 = _pr.nlargest(2, "리뷰수")
S["m_vol_top"] = [(r["Brand"], int(r["리뷰수"])) for _, r in _top2.iterrows()]
S["m_rating_mean"] = round(_pr["평점"].mean(), 2)
S["m_rating_min"] = round(_pr["평점"].min(), 1)
S["m_prod_with_rating"] = int(len(_pr))
# 리뷰 평점 분포
S["m_rev_n"] = len(m_rev)
_d = m_rev["평점"].value_counts().sort_index()
S["m_r5"] = int(_d.get(5, 0)); S["m_r5_pct"] = round(S["m_r5"] / S["m_rev_n"] * 100, 1)
S["m_r4"] = int(_d.get(4, 0)); S["m_r4_pct"] = round(S["m_r4"] / S["m_rev_n"] * 100, 1)
S["m_r3down"] = int((m_rev["평점"] <= 3).sum()); S["m_r3down_pct"] = round(S["m_r3down"] / S["m_rev_n"] * 100, 1)
S["m_4plus_pct"] = round((m_rev["평점"] >= 4).mean() * 100, 1)

# 채널 할인율 배율 (컬리169 / 무신사)
S["k_over_m_disc"] = round(S["k169_disc_med"] / S["m_disc_med"], 1)

# ── 무신사 리뷰 텍스트: 키워드 + 속성 언급률 ────────────────
STOP = set("있어요 있습니다 같아요 그리고 너무 정말 진짜 그냥 조금 아주 많이 잘 더 좀 것 수 때 거 "
           "저는 제가 근데 하고 입니다 있는 없이 같은 살짝 완전 계속 다시 하나 해서 위에 이번 다른 "
           "이거 봐요 봐서 그래서 하는 한 번 안 못 딱 좋아요 좋습니다 좋아서 좋고 좋음 굿 최고 "
           "만족합니다 만족해요 않고 엄청 생각보다 좋네요 마음에 입기 입고 입을 입어도".split())


def tokens(text):
    return [t for t in re.findall(r"[가-힣]{2,}", str(text)) if t not in STOP]


hi = m_rev[m_rev["평점"] >= 4]
lo = m_rev[m_rev["평점"] <= 3]
S["m_hi_n"] = len(hi)
S["m_lo_n"] = len(lo)

# 차트 12용 속성 사전 (노트북과 동일, 7종)
ASPECTS = {
    "사이즈": "사이즈|크기",
    "착용감": "편하|편안|불편",
    "시원함": "시원|여름|쿨",
    "소재/두께": "얇|소재|원단|두께",
    "컵/패드": "컵|와이어|패드|뽕",
    "마감/품질": "마감|봉제|박음질|실밥|품질",
    "배송": "배송",
}

# 섹션 06 표: 저평점 상승폭 큰 5속성 (기존 표 구성 유지)
TABLE_ASPECTS = [
    ("마감/품질 (실밥·봉제)", "마감|봉제|박음질|실밥|품질"),
    ("사이즈", "사이즈|크기"),
    ("컵/패드", "컵|와이어|패드|뽕"),
    ("착용감", "편하|편안|불편"),
    ("배송", "배송"),
]


def rate(df, pat):
    return df["Review Body"].str.contains(pat).mean() * 100


table_rows = []
for label, pat in TABLE_ASPECTS:
    hv = rate(hi, pat)
    lv = rate(lo, pat)
    ratio = (lv / hv) if hv > 0 else None
    table_rows.append((label, hv, lv, ratio))
S["table_rows"] = table_rows
# 헤더 KPI: 마감/품질 배율
_fin = next(r for r in table_rows if r[0].startswith("마감/품질"))
S["m_finish_ratio"] = round(_fin[3], 1) if _fin[3] else None

# ═══════════════════════════════════════════════════════════
# 차트 12종 (analysis 노트북과 동일 로직) → base64
# ═══════════════════════════════════════════════════════════
def _price_hist(prod, title):
    cap = int(prod["가격"].quantile(0.99))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(prod["가격"].clip(upper=cap), bins=20, color=BLUE, edgecolor=SURFACE, linewidth=2)
    med = prod["가격"].median()
    ax.axvline(med, color=INK, linewidth=1, linestyle="--")
    ax.text(med, ax.get_ylim()[1] * 0.95, f"  중앙값 {med:,.0f}원", va="top", fontsize=10)
    ax.set_xlabel("판매가 (원)"); ax.set_ylabel("상품 수")
    ax.set_title(title, loc="left", fontsize=13, pad=12)
    ax.grid(True, axis="y"); fig.tight_layout()
    return png_b64(fig)


def _kurly_discount_hist(prod):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(prod["할인율"], bins=range(0, prod["할인율"].max() + 11, 10),
            color=BLUE, edgecolor=SURFACE, linewidth=2)
    ax.set_xlabel("할인율 (%)"); ax.set_ylabel("상품 수")
    ax.set_title("할인율 분포", loc="left", fontsize=13, pad=12)
    ax.grid(True, axis="y"); fig.tight_layout()
    return png_b64(fig)


def _brand_barh(counts, xlabel):
    top = counts[counts >= 2].sort_values()
    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.34 * len(top))))
    ax.barh(top.index, top.values, color=BLUE, height=0.62)
    ax.set_xlabel(xlabel)
    ax.set_title("브랜드별 진입 상품 수 (2개 이상)", loc="left", fontsize=13, pad=12)
    ax.set_xticks(range(0, int(top.max()) + 1))
    ax.grid(True, axis="x"); fig.tight_layout()
    return png_b64(fig)


def _pareto(prod):
    s = prod["리뷰수"].sort_values(ascending=False).reset_index(drop=True)
    share = s.cumsum() / s.sum() * 100
    x = (s.index + 1) / len(s) * 100
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(x, share, color=BLUE, linewidth=2)
    p10 = share.iloc[max(0, int(len(s) * 0.1) - 1)]
    ax.scatter([10], [p10], s=64, color=BLUE, zorder=3, edgecolor=SURFACE, linewidth=1)
    ax.annotate(f"상위 10% 상품이 리뷰의 {p10:.0f}%", (10, p10),
                textcoords="offset points", xytext=(10, -4), fontsize=10, color=SECONDARY)
    ax.set_xlabel("상품 누적 비율 (%, 리뷰수 내림차순)")
    ax.set_ylabel("리뷰수 누적 비율 (%)"); ax.set_ylim(0, 105)
    ax.set_title("리뷰수 파레토 곡선", loc="left", fontsize=13, pad=12)
    ax.grid(True, axis="y"); fig.tight_layout()
    return png_b64(fig)


def _musinsa_price_hist(prod):
    top = -(-int(prod["가격"].max()) // 10000) * 10000  # 올림 10k
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(prod["가격"], bins=range(0, top + 1, 10000), color=BLUE, edgecolor=SURFACE, linewidth=2)
    med = prod["가격"].median()
    ax.axvline(med, color=INK, linewidth=1, linestyle="--")
    ax.text(med + 1500, ax.get_ylim()[1] * 0.95, f"중앙값 {med:,.0f}원", va="top", fontsize=10)
    ax.set_xticks(range(0, top + 1, 20000))
    ax.set_xticklabels([f"{x // 10000}만" if x else "0" for x in range(0, top + 1, 20000)])
    ax.set_xlabel("판매가 (원)"); ax.set_ylabel("상품 수")
    ax.set_title(f"인기 상위 {len(prod)}개 상품 가격 분포", loc="left", fontsize=13, pad=12)
    ax.grid(True, axis="y"); fig.tight_layout()
    return png_b64(fig)


def _musinsa_discount_hist(prod):
    top = max(80, -(-int(prod["할인율"].max()) // 10) * 10)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(prod["할인율"], bins=range(0, top + 1, 10), color=BLUE, edgecolor=SURFACE, linewidth=2)
    ax.set_xlabel("할인율 (%)"); ax.set_ylabel("상품 수")
    ax.set_title("할인율 분포", loc="left", fontsize=13, pad=12)
    ax.grid(True, axis="y"); fig.tight_layout()
    return png_b64(fig)


def _scatter(prod):
    p = prod[prod["평점"] > 0]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.scatter(p["리뷰수"], p["평점"], s=64, color=BLUE, alpha=0.75, edgecolor=SURFACE, linewidth=1)
    ax.set_xscale("log")
    for _, row in p.nlargest(2, "리뷰수").iterrows():
        ax.annotate(row["Brand"], (row["리뷰수"], row["평점"]),
                    textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9, color=SECONDARY)
    ax.set_xlabel("리뷰 수 (로그 스케일)"); ax.set_ylabel("평점 (5점 만점)")
    ax.set_title("리뷰 수 vs 평점", loc="left", fontsize=13, pad=12)
    fig.tight_layout()
    return png_b64(fig)


def _rating_dist(rev):
    dist = rev["평점"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar(dist.index, dist.values, color=BLUE, width=0.62)
    for b, v in zip(bars, dist.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 6, f"{v}건 ({v / len(rev):.1%})",
                ha="center", fontsize=10, color=SECONDARY)
    ax.set_xlabel("리뷰 평점"); ax.set_ylabel("리뷰 수"); ax.set_ylim(0, dist.max() * 1.15)
    ax.set_title(f"리뷰 평점 분포 ({len(rev)}건)", loc="left", fontsize=13, pad=12)
    ax.grid(True, axis="y"); fig.tight_layout()
    return png_b64(fig)


def _keywords(hi_df):
    top15 = pd.Series(Counter(t for s in hi_df["Review Body"] for t in tokens(s))).nlargest(15)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(top15.index[::-1], top15.values[::-1], color=BLUE, height=0.62)
    ax.set_xlabel("언급 횟수")
    ax.set_title(f"고평점(4~5점) 리뷰 빈출 키워드 (n={len(hi_df)})", loc="left", fontsize=13, pad=12)
    ax.grid(True, axis="x"); fig.tight_layout()
    return png_b64(fig), list(top15.index[:6])


def _aspect_rates(hi_df, lo_df):
    rates = pd.DataFrame({
        "고평점(4~5점)": [rate(hi_df, p) for p in ASPECTS.values()],
        "저평점(1~3점)": [rate(lo_df, p) for p in ASPECTS.values()],
    }, index=ASPECTS.keys())
    y = range(len(rates)); h = 0.36
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh([i - h / 2 for i in y], rates["고평점(4~5점)"], height=h - 0.04, color=BLUE,
            label=f"고평점 4~5점 (n={len(hi_df)})")
    ax.barh([i + h / 2 for i in y], rates["저평점(1~3점)"], height=h - 0.04, color=RED,
            label=f"저평점 1~3점 (n={len(lo_df)})")
    for i, (hv, lv) in enumerate(zip(rates["고평점(4~5점)"], rates["저평점(1~3점)"])):
        ax.text(hv + 0.7, i - h / 2, f"{hv:.0f}%", va="center", fontsize=9, color=SECONDARY)
        ax.text(lv + 0.7, i + h / 2, f"{lv:.0f}%", va="center", fontsize=9, color=SECONDARY)
    ax.set_yticks(list(y)); ax.set_yticklabels(rates.index); ax.invert_yaxis()
    ax.set_xlabel("해당 속성을 언급한 리뷰 비율 (%)")
    ax.set_title("평점 그룹별 속성 언급률", loc="left", fontsize=13, pad=12)
    ax.legend(frameon=False, loc="lower right"); ax.grid(True, axis="x"); fig.tight_layout()
    return png_b64(fig)


# ═══════════════════════════════════════════════════════════
# 재현성 점검 — 직전 스냅샷과 자동 대조 (스냅샷이 1개뿐이면 생략)
# ═══════════════════════════════════════════════════════════
def _snap_pair(pattern):
    files = sorted(f for f in glob(pattern) if "_raw" not in f)
    return (files[-2], files[-1]) if len(files) >= 2 else None


def _date_of(path):
    m = re.search(r"(\d{4})(\d{2})(\d{2})", path)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def build_comparison():
    mrev = _snap_pair(f"{MUSINSA_DIR}/reviews_026_*.json")
    mprod = _snap_pair(f"{MUSINSA_DIR}/products_026_*.json")
    p169 = _snap_pair(f"{KURLY_DIR}/kurly_products_169_*.json")
    p166 = _snap_pair(f"{KURLY_DIR}/kurly_products_166_*.json")
    p165 = _snap_pair(f"{KURLY_DIR}/kurly_products_165_*.json")
    if not (mrev and mprod and p169 and p166):
        return {"enabled": False}

    def rating4(path):
        r = pd.DataFrame(json.load(open(path, encoding="utf-8")))
        return round(pd.to_numeric(r["Rating"], errors="coerce").ge(4).mean() * 100, 1)

    def disc25(path):
        d = pd.DataFrame(json.load(open(path, encoding="utf-8")))
        v = pd.to_numeric(d["Discount Rate"].astype(str).str.rstrip("%"), errors="coerce").fillna(0)
        return round(v.ge(25).mean() * 100)

    def disc_by_goods(path):
        d = pd.DataFrame(json.load(open(path, encoding="utf-8")))
        d["v"] = pd.to_numeric(d["Discount Rate"].astype(str).str.rstrip("%"), errors="coerce").fillna(0).astype(int)
        return d.set_index("_goods_no")["v"]

    def persist(pair):
        o = set(pd.DataFrame(json.load(open(pair[0], encoding="utf-8")))["_goods_no"])
        n = set(pd.DataFrame(json.load(open(pair[1], encoding="utf-8")))["_goods_no"])
        return round(len(o & n) / len(o) * 100)

    # 컬리166 — 유지 상품만의 할인율 중앙값 (표본 교체가 아닌 실제 리프라이싱)
    o166, n166 = disc_by_goods(p166[0]), disc_by_goods(p166[1])
    keep166 = o166.index.intersection(n166.index)

    old_dates = sorted({_date_of(mprod[0]), _date_of(p169[0])})
    old_label = old_dates[0] if len(old_dates) == 1 else f"{old_dates[0]}~{old_dates[-1][8:]}"
    k_persist = round(sum(persist(x) for x in (p165, p166, p169)) / 3)
    return {
        "enabled": True,
        "old_label": old_label,
        "new_label": _date_of(p169[1]),
        "m_4plus_old": rating4(mrev[0]), "m_4plus_new": rating4(mrev[1]),
        "k169_25_old": disc25(p169[0]), "k169_25_new": disc25(p169[1]),
        "k166_keep_n": int(len(keep166)),
        "k166_disc_old": int(o166.loc[keep166].median()),
        "k166_disc_new": int(n166.loc[keep166].median()),
        "m_persist": persist(mprod),
        "k_persist": k_persist,
    }


def build_charts():
    c = {}
    c["k169_price"] = _price_hist(k169, f"컬리 {k169['_name'].iloc[0]} 추천 상위 {len(k169)}개 상품 가격 분포")
    c["k169_disc"] = _kurly_discount_hist(k169)
    c["k169_brand"] = _brand_barh(k169[k169["브랜드"] != "(미표기)"]["브랜드"].value_counts(),
                                  f"추천 상위 {len(k169)}위 내 상품 수")
    c["k166_price"] = _price_hist(k166, f"컬리 {k166['_name'].iloc[0]} 추천 상위 {len(k166)}개 상품 가격 분포")
    c["k166_pareto"] = _pareto(k166)
    c["m_price"] = _musinsa_price_hist(m_prod)
    c["m_disc"] = _musinsa_discount_hist(m_prod)
    c["m_brand"] = _brand_barh(m_prod["Brand"].value_counts(), f"인기 상위 {len(m_prod)}위 내 상품 수")
    c["m_scatter"] = _scatter(m_prod)
    c["m_rating"] = _rating_dist(m_rev)
    c["m_keywords"], kw = _keywords(hi)
    c["m_aspects"] = _aspect_rates(hi, lo)
    return c, kw


def main():
    from build_portfolio_combined_html import render  # HTML 템플릿 (동일 폴더)
    charts, kw = build_charts()
    comp = build_comparison()
    html = render(S, charts, kw, COLLECT_DATE, comp)
    import os
    os.makedirs("output", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"저장 완료: {OUT_PATH} ({len(html.encode('utf-8')) // 1024} KB, 차트 12종)")


if __name__ == "__main__":
    main()
