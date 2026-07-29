# -*- coding: utf-8 -*-
"""data/*.csv → payload → output/kidswear_diagnosis.html.

2단계 스크립트. 커밋된 data/ 만 읽으므로 원본 없이도 실행된다.
"""
import html as _html
import os

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "output", "kidswear_diagnosis.html")

SEASONAL_ETC = ["한복", "파티·이벤트용품", "수영"]   # category_etc.csv 에 있는 것
SEASONAL_MAIN = ["아우터"]                            # category.csv 에 있는 것
PROPOSAL1_ITEMS = ["잠옷", "장화", "샌들"]


def _read(name, index_col=0):
    return pd.read_csv(os.path.join(DATA, name), encoding="utf-8-sig",
                       index_col=index_col)


def build_payload():
    meta_row = _read("meta.csv", index_col=None).iloc[0]
    pareto = _read("pareto.csv")
    delivery = _read("delivery.csv")
    brand = _read("brand.csv")
    category = _read("category.csv")
    cat_dv = _read("category_delivery.csv")
    price_dv = _read("price_delivery.csv")
    brand_dv = _read("brand_delivery.csv")
    cat_etc = _read("category_etc.csv")

    meta = {
        "n_sku": int(meta_row["n_sku"]),
        "n_reviews": int(meta_row["n_reviews"]),
        "n_brands": int(meta_row["n_brands"]),
        "n_reviewed_sku": int(meta_row["n_reviewed_sku"]),
        "n_zero_sku": int(meta_row["n_zero_sku"]),
        "gini": float(meta_row["gini"]),
        "snapshot": str(meta_row["snapshot"]),
        "reviewed_share": round(int(meta_row["n_reviewed_sku"])
                                / int(meta_row["n_sku"]) * 100, 1),
        "top1pct_share": float(pareto.loc["1%", "리뷰점유율%"]),
    }

    payload = {
        "meta": meta,
        "pareto": [{"label": i, "sku": int(r["SKU수"]), "cum": int(r["누적리뷰"]),
                    "share": float(r["리뷰점유율%"])}
                   for i, r in pareto.iterrows()],
        "delivery": [{"type": i, "sku": int(r["SKU수"]),
                      "zero_sku": int(r["리뷰0_SKU"]), "zero_pct": float(r["리뷰0_비율%"]),
                      "reviews": int(r["총리뷰수"]), "density": float(r["리뷰per_SKU"])}
                     for i, r in delivery.iterrows()],
        "brand": [{"brand": i, "sku": int(r["SKU수"]), "reviews": int(r["총리뷰수"]),
                   "density": float(r["리뷰per_SKU"]), "price": int(r["평균가격"])}
                  for i, r in brand.iterrows()],
        "category": [{"item": i, "sku": int(r["SKU수"]), "sku_share": float(r["SKU비중%"]),
                      "reviews": int(r["총리뷰수"]), "review_share": float(r["리뷰비중%"]),
                      "density": float(r["리뷰밀도"]), "price": int(r["평균가격"])}
                     for i, r in category.iterrows()],
        "category_delivery": [{"item": i,
                               "dawn_sku": int(r["SKU_샛별배송"]),
                               "dawn_reviews": int(r["리뷰_샛별배송"]),
                               "seller_sku": int(r["SKU_판매자배송"]),
                               "seller_reviews": int(r["리뷰_판매자배송"])}
                              for i, r in cat_dv.iterrows()],
        "price_delivery": [{"price": i, "delivery": dv,
                            "sku": int(r[f"SKU_{dv}"]),
                            "reviews": int(r[f"리뷰_{dv}"]),
                            "density": float(r[f"밀도_{dv}"])}
                           for i, r in price_dv.iterrows()
                           for dv in ("샛별배송", "판매자배송")],
        "brand_delivery": [{"brand": i,
                            "dawn_sku": int(r["SKU_샛별배송"]),
                            "dawn_reviews": int(r["리뷰_샛별배송"]),
                            "dawn_density": float(r["밀도_샛별배송"]),
                            "dawn_price": int(r["평균가_샛별배송"]),
                            "seller_sku": int(r["SKU_판매자배송"]),
                            "seller_reviews": int(r["리뷰_판매자배송"]),
                            "seller_density": float(r["밀도_판매자배송"]),
                            "seller_price": int(r["평균가_판매자배송"])}
                           for i, r in brand_dv.iterrows()],
        "category_etc": [{"item": i, "sku": int(r["SKU수"]),
                          "reviews": int(r["총리뷰수"]), "price": int(r["평균가격"])}
                         for i, r in cat_etc.iterrows()],
    }
    payload["derived"] = _derive(payload, cat_dv, category, cat_etc)
    return payload


def _density(reviews, sku):
    return round(reviews / sku, 2) if sku else 0.0


def _derive(payload, cat_dv, category, cat_etc):
    """대시보드가 직접 주장하는 파생 지표. 여기서 한 번만 계산한다."""
    dawn_lift = []
    for item in ("실내화", "학용품"):
        r = cat_dv.loc[item]
        seller = _density(r["리뷰_판매자배송"], r["SKU_판매자배송"])
        dawn = _density(r["리뷰_샛별배송"], r["SKU_샛별배송"])
        dawn_lift.append({
            "item": item,
            "seller_sku": int(r["SKU_판매자배송"]), "seller_reviews": int(r["리뷰_판매자배송"]),
            "seller_density": seller,
            "dawn_sku": int(r["SKU_샛별배송"]), "dawn_reviews": int(r["리뷰_샛별배송"]),
            "dawn_density": dawn,
            "multiple": round(dawn / seller, 1),
        })

    proposal1 = []
    for item in PROPOSAL1_ITEMS:
        r = cat_dv.loc[item]
        proposal1.append({
            "item": item,
            "dawn_sku": int(r["SKU_샛별배송"]),
            "seller_sku": int(r["SKU_판매자배송"]),
            "seller_reviews": int(r["리뷰_판매자배송"]),
            "seller_density": _density(r["리뷰_판매자배송"], r["SKU_판매자배송"]),
        })

    rows = []
    for item in SEASONAL_ETC:
        r = cat_etc.loc[item]
        rows.append({"item": item, "sku": int(r["SKU수"]), "reviews": int(r["총리뷰수"])})
    for item in SEASONAL_MAIN:
        r = category.loc[item]
        rows.append({"item": item, "sku": int(r["SKU수"]), "reviews": int(r["총리뷰수"])})
    rows.sort(key=lambda x: -x["sku"])
    total_sku = sum(r["sku"] for r in rows)
    total_reviews = sum(r["reviews"] for r in rows)
    seasonal = {
        "rows": rows,
        "total_sku": total_sku,
        "total_reviews": total_reviews,
        "sku_share": round(total_sku / payload["meta"]["n_sku"] * 100, 1),
        "review_share": round(total_reviews / payload["meta"]["n_reviews"] * 100, 1),
    }
    return {"dawn_lift": dawn_lift, "proposal1": proposal1, "seasonal": seasonal}


FONT = ('"Pretendard Variable", Pretendard, "Apple SD Gothic Neo", '
        '"Noto Sans KR", "Malgun Gothic", system-ui, sans-serif')

CSS = """
:root{--ground:#fcfcfb;--panel:#f5f5f1;--ink:#0b0b0b;--secondary:#52514e;
--muted:#898781;--hairline:#e1e0d9;--blue:#2a78d6;--blue-soft:#e8f0fb;
--red:#e34948;--kurly:#5f0080;--kurly-soft:#f3e9f7;}
@media (prefers-color-scheme:dark){:root{--ground:#171613;--panel:#201f1b;
--ink:#f0efe9;--secondary:#b5b3ab;--muted:#85837b;--hairline:#34322c;
--blue:#6aa5e8;--blue-soft:#1d2a3c;--red:#ef7a79;--kurly:#c78ae0;--kurly-soft:#33203d;}}
:root[data-theme="dark"]{--ground:#171613;--panel:#201f1b;--ink:#f0efe9;
--secondary:#b5b3ab;--muted:#85837b;--hairline:#34322c;--blue:#6aa5e8;
--blue-soft:#1d2a3c;--red:#ef7a79;--kurly:#c78ae0;--kurly-soft:#33203d;}
:root[data-theme="light"]{--ground:#fcfcfb;--panel:#f5f5f1;--ink:#0b0b0b;
--secondary:#52514e;--muted:#898781;--hairline:#e1e0d9;--blue:#2a78d6;
--blue-soft:#e8f0fb;--red:#e34948;--kurly:#5f0080;--kurly-soft:#f3e9f7;}
*{box-sizing:border-box}
html{background:var(--ground)}
body{margin:0;background:var(--ground);color:var(--ink);font-family:FONT_STACK;
font-size:16px;line-height:1.72;-webkit-font-smoothing:antialiased}
.page{max-width:860px;margin:0 auto;padding:48px 24px 80px}
.prose{max-width:72ch}
.eyebrow{font-size:12px;letter-spacing:.14em;color:var(--muted);font-weight:600;
margin:0 0 14px;text-transform:uppercase}
h1{font-size:clamp(28px,5.2vw,42px);line-height:1.22;letter-spacing:-.022em;
font-weight:800;margin:0 0 18px;text-wrap:balance}
h2{font-size:clamp(20px,3vw,26px);line-height:1.3;letter-spacing:-.018em;
font-weight:800;margin:64px 0 14px}
h3{font-size:17px;font-weight:700;margin:32px 0 10px}
.thesis{font-size:clamp(16px,2.2vw,19px);line-height:1.62;color:var(--secondary);
margin:0 0 24px;max-width:60ch;text-wrap:balance}
.thesis strong{color:var(--ink);font-weight:700}
p{margin:0 0 14px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px}
.chip{display:inline-flex;align-items:baseline;gap:6px;font-size:13px;
background:var(--panel);border:1px solid var(--hairline);border-radius:99px;
padding:5px 13px}
.chip b{font-weight:800;font-variant-numeric:tabular-nums}
.act{border-top:1px solid var(--hairline);margin-top:56px;padding-top:8px}
.figure{margin:24px 0}
.figure figcaption{font-size:13px;color:var(--muted);margin-top:8px}
.scroller{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px;
font-variant-numeric:tabular-nums;min-width:420px}
th,td{padding:8px 10px;border-bottom:1px solid var(--hairline);text-align:right}
th:first-child,td:first-child{text-align:left}
thead th{color:var(--muted);font-weight:600;font-size:12.5px}
.note{background:var(--panel);border:1px solid var(--hairline);border-radius:10px;
padding:16px 18px;font-size:14px;color:var(--secondary);margin:20px 0}
.note b{color:var(--ink)}
ol,ul{padding-left:20px;margin:0 0 14px}
li{margin:6px 0}
@media (max-width:520px){.page{padding:32px 16px 56px}}
"""


def _esc(s):
    return _html.escape(str(s))


def _snapshot_label(snapshot):
    """'20260728_161036' -> '2026.07'. 재수집하면 라벨이 자동으로 따라간다."""
    return f"{snapshot[:4]}.{snapshot[4:6]}"


def render_head(p):
    css = CSS.replace("FONT_STACK", FONT)
    n = p["meta"]["n_sku"]
    return (
        '<!doctype html>\n<html lang="ko">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>컬리 키즈웨어 카탈로그 진단 — {n:,} SKU 전수 분석</title>\n"
        f"<style>{css}</style>\n</head>\n<body>\n"
    )


def render_poster(p):
    """iframe 640px 안에 들어가는 영역. 결론을 여기 둔다.

    `<div class="page">` 를 여기서 열고, `render_html` 이 닫는다 —
    Task 4·5 가 그 사이에 자기 섹션을 끼워 넣는다.
    """
    m = p["meta"]
    return f"""<div class="page">
<p class="eyebrow">Kurly Kidswear · {_snapshot_label(m['snapshot'])} · {m['n_sku']:,} SKU 전수</p>
<h1>{m['n_sku']:,}개의 카탈로그, 수요는 상위 1%에 몰려 있다</h1>
<p class="thesis">리뷰가 붙은 상품은 {m['n_reviewed_sku']}개({m['reviewed_share']}%).
남은 {m['n_zero_sku']:,}개가 나쁜 상품이라는 뜻은 아니다 —
<strong>팔리는 조합이 좁을 뿐</strong>이고, 그 조합이 무엇인지는 데이터가 특정해준다.</p>
<div class="chips">
<span class="chip"><b>{m['n_sku']:,}</b> SKU</span>
<span class="chip"><b>{m['n_brands']}</b> 브랜드</span>
<span class="chip">지니 <b>{m['gini']:.3f}</b></span>
<span class="chip">상위 1% = 리뷰 <b>{m['top1pct_share']}%</b></span>
</div>
"""


def render_html(payload):
    parts = [render_head(payload), render_poster(payload)]
    # Task 4 가 1막·2막을, Task 5 가 3막·부록을 여기에 추가한다
    parts.append("</div>\n</body>\n</html>\n")
    return "".join(parts)


def main():
    payload = build_payload()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render_html(payload))
    print(f"생성: {OUT}")


if __name__ == "__main__":
    main()
