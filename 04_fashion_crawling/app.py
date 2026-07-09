"""수집 데이터 대시보드 (Gradio).

data/ 폴더의 수집 결과(컬리·무신사)를 자동 인식해 카테고리별
가격 분포 · 할인 구조 · 브랜드 구도 · 리뷰 키워드를 보여줍니다.

실행:
    pip install -r requirements.txt
    python app.py          # 브라우저에서 http://127.0.0.1:7860

새로 수집한 데이터는 화면의 '데이터 다시 읽기' 버튼으로 반영합니다.
"""

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 서버 렌더링 — GUI 백엔드 불필요
import gradio as gr
import matplotlib.pyplot as plt
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# 차트 팔레트 — analysis.ipynb / analysis_kurly.ipynb와 동일
BLUE = "#2a78d6"
INK, SECONDARY, MUTED = "#0b0b0b", "#52514e", "#898781"
SURFACE = "#fcfcfb"

# 설치된 한글 폰트를 골라 하나만 지정 (리스트로 주면 없는 폰트마다 경고가 나옴)
from matplotlib import font_manager

_KOREAN_FONTS = ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR")
_available = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in _KOREAN_FONTS if f in _available), "DejaVu Sans")

plt.rcParams.update({
    "font.family": FONT,
    "axes.unicode_minus": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": "#c3c2b7",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": False, "grid.color": "#e1e0d9", "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "text.color": INK, "axes.labelcolor": SECONDARY,
    "xtick.color": MUTED, "ytick.color": MUTED,
})

STOP = set('있어요 있습니다 같아요 그리고 너무 정말 진짜 그냥 조금 아주 많이 잘 더 좀 것 수 때 거 '
           '저는 제가 근데 하고 입니다 있는 없이 같은 살짝 완전 계속 다시 하나 해서 위에 이번 다른 '
           '이거 봐요 봐서 그래서 하는 한 번 안 못 딱 좋아요 좋습니다 좋아서 좋고 좋음 굿 최고 '
           '만족합니다 만족해요 않고 엄청 생각보다 좋네요 마음에 입기 입고 입을 입어도 구매 주문'.split())


# ---------------------------------------------------------------------------
# 데이터 검색 · 로드
# ---------------------------------------------------------------------------

def discover_datasets() -> dict[str, dict]:
    """data/의 products 파일을 (채널·카테고리)별 최신본으로 정리.

    반환: {표시 라벨: {"products": Path, "reviews": Path | None}}
    """
    latest: dict[str, Path] = {}
    for path in sorted(DATA_DIR.glob("*products_*.json")):
        m = re.match(r"^(kurly_)?products_(.+)_(\d{8})$", path.stem)
        if m:
            latest[f"{m.group(1) or ''}{m.group(2)}"] = path  # 정렬 순서상 마지막(최신)이 남음

    datasets: dict[str, dict] = {}
    for key, ppath in latest.items():
        try:
            rows = json.loads(ppath.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not rows:
            continue
        channel = rows[0].get("Channel", "?")
        category = rows[0].get("Category", key)
        rev_glob = ppath.name.replace("products", "reviews").rsplit("_", 1)[0]
        # --dump-raw가 만든 *_raw.json(API 원본)은 리뷰 데이터가 아니므로 제외
        rev_files = sorted(p for p in DATA_DIR.glob(f"{rev_glob}_*.json")
                           if not p.stem.endswith("_raw"))
        datasets[f"{channel} · {category}"] = {
            "products": ppath,
            "reviews": rev_files[-1] if rev_files else None,
        }
    return datasets


def load_products(path: Path) -> pd.DataFrame:
    prod = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    prod["가격"] = pd.to_numeric(prod["Price"].str.replace(",", ""), errors="coerce")
    prod = prod.dropna(subset=["가격"])
    prod["가격"] = prod["가격"].astype(int)
    prod["할인율"] = pd.to_numeric(
        prod["Discount Rate"].str.rstrip("%"), errors="coerce").fillna(0).astype(int)
    # 컬리는 '999+' 상한 표기 — 숫자만 남김
    prod["리뷰수"] = pd.to_numeric(
        prod["Review Count"].str.replace(",", "").str.rstrip("+"),
        errors="coerce").fillna(0).astype(int)
    prod["브랜드"] = prod["Brand"].replace("", "(미표기)")
    return prod


def load_reviews(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    return pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# 차트
# ---------------------------------------------------------------------------

def _fig(figsize=(6.5, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


def _empty_fig(message: str):
    fig, ax = _fig()
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, color=MUTED)
    ax.axis("off")
    return fig


def price_fig(prod: pd.DataFrame):
    fig, ax = _fig()
    cap = int(prod["가격"].quantile(0.99))
    ax.hist(prod["가격"].clip(upper=cap), bins=20, color=BLUE,
            edgecolor=SURFACE, linewidth=2)
    med = prod["가격"].median()
    ax.axvline(med, color=INK, linewidth=1, linestyle="--")
    ax.text(med, ax.get_ylim()[1] * 0.95, f"  중앙값 {med:,.0f}원", va="top", fontsize=9)
    ax.set_xlabel("판매가 (원)")
    ax.set_ylabel("상품 수")
    ax.set_title(f"가격 분포 (n={len(prod)})", loc="left", fontsize=12, pad=10)
    ax.grid(True, axis="y")
    fig.tight_layout()
    return fig


def discount_fig(prod: pd.DataFrame):
    fig, ax = _fig()
    ax.hist(prod["할인율"], bins=range(0, int(prod["할인율"].max()) + 11, 10),
            color=BLUE, edgecolor=SURFACE, linewidth=2)
    ax.set_xlabel("할인율 (%)")
    ax.set_ylabel("상품 수")
    ax.set_title("할인율 분포", loc="left", fontsize=12, pad=10)
    ax.grid(True, axis="y")
    fig.tight_layout()
    return fig


def brand_fig(prod: pd.DataFrame):
    cnt = prod.loc[prod["브랜드"] != "(미표기)", "브랜드"].value_counts()
    top = cnt[cnt >= 2].sort_values().tail(12)
    if top.empty:
        return _empty_fig("2개 이상 진입한 브랜드가 없습니다")
    fig, ax = _fig()
    ax.barh(top.index, top.values, color=BLUE, height=0.62)
    ax.set_xlabel("상위 노출 상품 수")
    ax.set_title("브랜드별 진입 상품 수 (2개 이상)", loc="left", fontsize=12, pad=10)
    ax.set_xticks(range(0, int(top.max()) + 1))
    ax.grid(True, axis="x")
    fig.tight_layout()
    return fig


def keyword_fig(rev: pd.DataFrame):
    if rev.empty or "Review Body" not in rev.columns:
        return _empty_fig("리뷰 데이터가 없습니다\n(크롤러의 reviews 명령으로 수집)")
    words = Counter(
        t for s in rev["Review Body"]
        for t in re.findall(r"[가-힣]{2,}", str(s)) if t not in STOP
    )
    top15 = pd.Series(words).nlargest(15)
    fig, ax = _fig()
    ax.barh(top15.index[::-1], top15.values[::-1], color=BLUE, height=0.62)
    ax.set_xlabel("언급 횟수")
    ax.set_title(f"리뷰 빈출 키워드 (n={len(rev)})", loc="left", fontsize=12, pad=10)
    ax.grid(True, axis="x")
    fig.tight_layout()
    return fig


def summary_md(prod: pd.DataFrame, rev: pd.DataFrame) -> str:
    parts = [
        f"**상품 {len(prod):,}개**",
        f"가격 중앙값 **{prod['가격'].median():,.0f}원**",
        f"할인율 중앙값 **{prod['할인율'].median():.0f}%**",
        f"정가 판매 **{(prod['할인율'] == 0).mean():.0%}**",
        f"리뷰 **{len(rev):,}건**" if len(rev) else "리뷰 미수집",
    ]
    return " · ".join(parts)


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def render(label: str, datasets: dict):
    if not label or label not in datasets:
        empty = _empty_fig("데이터가 없습니다")
        return ("`data/` 폴더에 수집 파일이 없습니다. "
                "`kurly_crawler.py` / `musinsa_crawler.py`를 먼저 실행하세요."), \
            empty, empty, empty, empty
    ds = datasets[label]
    prod = load_products(ds["products"])
    rev = load_reviews(ds["reviews"])
    plt.close("all")  # 이전 렌더링 figure 정리
    return (summary_md(prod, rev), price_fig(prod), discount_fig(prod),
            brand_fig(prod), keyword_fig(rev))


def build_app():
    with gr.Blocks(title="패션 커머스 수집 데이터 대시보드") as demo:
        datasets_state = gr.State(discover_datasets())
        initial = list(datasets_state.value.keys())

        gr.Markdown("# 패션 커머스 수집 데이터 대시보드")
        with gr.Row():
            dataset = gr.Dropdown(choices=initial, value=initial[0] if initial else None,
                                  label="채널 · 카테고리", scale=4)
            reload_btn = gr.Button("데이터 다시 읽기", scale=1)
        summary = gr.Markdown()
        with gr.Row():
            price_plot = gr.Plot(label="가격")
            discount_plot = gr.Plot(label="할인")
        with gr.Row():
            brand_plot = gr.Plot(label="브랜드")
            keyword_plot = gr.Plot(label="리뷰 키워드")

        outputs = [summary, price_plot, discount_plot, brand_plot, keyword_plot]

        dataset.change(render, [dataset, datasets_state], outputs)
        demo.load(render, [dataset, datasets_state], outputs)

        def reload_data():
            ds = discover_datasets()
            keys = list(ds.keys())
            return ds, gr.Dropdown(choices=keys, value=keys[0] if keys else None)

        reload_btn.click(reload_data, None, [datasets_state, dataset]) \
            .then(render, [dataset, datasets_state], outputs)

    return demo


if __name__ == "__main__":
    build_app().launch()
