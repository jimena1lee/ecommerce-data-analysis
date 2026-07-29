# -*- coding: utf-8 -*-
"""data/*.csv → payload → output/kidswear_diagnosis.html.

2단계 스크립트. 커밋된 data/ 만 읽으므로 원본 없이도 실행된다.
"""
import os

import pandas as pd

from svg_charts import heatmap_2x2, mirror_bars, pareto_curve, slope

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


def _snapshot_label(snapshot):
    """'20260728_161036' -> '2026.07'. 재수집하면 라벨이 자동으로 따라간다."""
    return f"{snapshot[:4]}.{snapshot[4:6]}"


def _snapshot_date(snapshot):
    """'20260728_161036' -> '2026-07-28'. 부록의 전체 날짜 표기용."""
    return f"{snapshot[:4]}-{snapshot[4:6]}-{snapshot[6:8]}"


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


def render_act1(p):
    m = p["meta"]
    cat = {c["item"]: c for c in p["category"]}
    apparel_sku = round(sum(cat[i]["sku_share"] for i in ("상의", "하의", "아우터")), 1)
    apparel_rv = round(sum(cat[i]["review_share"] for i in ("상의", "하의", "아우터")), 1)
    quick_sku = round(sum(cat[i]["sku_share"] for i in ("실내화", "학용품")), 1)
    quick_rv = round(sum(cat[i]["review_share"] for i in ("실내화", "학용품")), 1)
    return f"""<section class="act">
<h2>1막 · 무엇이 안 팔리는가</h2>
<div class="prose">
<p>리뷰 상위 1%인 {p['pareto'][0]['sku']}개 상품이 전체 리뷰의
{p['pareto'][0]['share']}%를 가져간다. 상위 5%면 {p['pareto'][1]['share']}%다.
통상적인 파레토(상위 20%가 80%)보다 훨씬 가파르다 — 지니계수 {m['gini']:.3f}.</p>
</div>
<figure class="figure">{pareto_curve(p['pareto'][:4])}
<figcaption>리뷰수 내림차순 상위 n% 상품이 차지하는 누적 리뷰 점유율.
20% 지점에서 이미 100%다 — 나머지 80%는 리뷰가 0이다.</figcaption></figure>
<div class="prose">
<p>어디에 몰려 있는지를 보면 배분 문제가 드러난다. 의류(상의·하의·아우터)는
SKU 의 {apparel_sku}%를 쓰면서 리뷰는 {apparel_rv}%다. 반대로 실내화·학용품은
SKU {quick_sku}%로 리뷰의 {quick_rv}%를 만든다.</p>
</div>
<figure class="figure"><div class="scroller">{mirror_bars(p['category'])}</div>
<figcaption>품목별 SKU 비중(좌)과 리뷰 비중(우). 두 막대의 길이가 어긋난 정도가
카탈로그 배분과 실수요의 간극이다.</figcaption></figure>
</section>
"""


def render_act2(p):
    lift = {d["item"]: d for d in p["derived"]["dawn_lift"]}
    cells = {(c["price"], c["delivery"]): c for c in p["price_delivery"]}
    lo_dawn = cells[("2만원 미만", "샛별배송")]["density"]
    lo_sell = cells[("2만원 미만", "판매자배송")]["density"]
    hi_dawn = cells[("2만원 이상", "샛별배송")]["density"]
    hi_sell = cells[("2만원 이상", "판매자배송")]["density"]
    cd = {c["item"]: c for c in p["category_delivery"]}
    hkp = next(b for b in p["brand_delivery"] if b["brand"] == "하우키즈풀")
    return f"""<section class="act">
<h2>2막 · 무엇이 변수인가</h2>
<div class="prose">
<p>품목이 아니라 <strong>어떻게 파느냐</strong>가 갈랐다. 가격대와 배송타입으로
카탈로그를 네 칸으로 나누면 순서가 깨끗하게 정렬된다.</p>
</div>
<figure class="figure"><div class="scroller">{heatmap_2x2(p['price_delivery'])}</div>
<figcaption>2만원을 기준으로 나눈 가격대 × 배송타입. 역전 없이 단조 감소한다.</figcaption>
</figure>
<div class="prose">
<p>두 변수 모두 유효하지만 크기가 다르다. 배송타입을 바꿨을 때가
{round(lo_dawn / lo_sell)}배(저가) · {round(hi_dawn / hi_sell)}배(고가),
가격대를 바꿨을 때가 {round(lo_dawn / hi_dawn, 1)}배(샛별) ·
{round(lo_sell / hi_sell, 1)}배(판매자)다. <strong>배송타입이 1차 변수</strong>다.</p>
<h3>같은 품목, 다른 배송타입</h3>
<p>"그 품목이 원래 잘 팔려서"라는 설명은 성립하지 않는다. 같은 품목 안에서
배송타입만 다른 쌍이 있기 때문이다. 특히 학용품은 SKU 수가
{cd['학용품']['seller_sku']}개 대 {cd['학용품']['dawn_sku']}개로 거의 같은데
리뷰밀도가 {round(lift['학용품']['multiple'])}배 차이난다.</p>
</div>
<figure class="figure">{slope(p['derived']['dawn_lift'])}
<figcaption>판매자배송과 샛별배송에 같은 품목이 동시에 있는 두 사례.
선의 기울기가 배송타입 효과다.</figcaption></figure>
<div class="prose">
<h3>같은 브랜드, 다른 배송타입</h3>
<p>브랜드도 변수가 아니다. 하우키즈풀 한 브랜드 안에서 갈린다.</p>
</div>
<div class="scroller"><table>
<thead><tr><th>하우키즈풀</th><th>SKU</th><th>리뷰</th><th>SKU당</th><th>평균가</th></tr></thead>
<tbody>
<tr><td>샛별배송</td><td>{hkp['dawn_sku']}</td><td>{hkp['dawn_reviews']}</td>
<td>{hkp['dawn_density']:g}</td><td>{hkp['dawn_price']:,}원</td></tr>
<tr><td>판매자배송</td><td>{hkp['seller_sku']}</td><td>{hkp['seller_reviews']}</td>
<td>{hkp['seller_density']:g}</td><td>{hkp['seller_price']:,}원</td></tr>
</tbody></table></div>
<div class="note"><b>정리.</b> 팔리는 조합은 <b>저가 × 샛별배송</b> 하나다.
나머지 세 칸은 SKU 를 아무리 늘려도 리뷰가 붙지 않는다.
카탈로그 크기가 아니라 조합이 문제다.</div>
</section>
"""


def render_act3(p):
    s = p["derived"]["seasonal"]
    lift = {d["item"]: d for d in p["derived"]["dawn_lift"]}
    cand = p["derived"]["proposal1"]
    cd = {c["item"]: c for c in p["category_delivery"]}
    # 판매자배송 기준 리뷰밀도. category.csv 의 전체(샛별+판매자) 리뷰밀도를 쓰면
    # 바로 아래 표(판매자배송 전용)와 기준이 어긋난다 — 반드시 이 값을 인용한다.
    top_density = _density(cd["상의"]["seller_reviews"], cd["상의"]["seller_sku"])
    bottom_density = _density(cd["하의"]["seller_reviews"], cd["하의"]["seller_sku"])
    outer_density = _density(cd["아우터"]["seller_reviews"], cd["아우터"]["seller_sku"])

    rows1 = "".join(
        f"<tr><td>{c['item']}</td><td>{c['seller_sku']}</td>"
        f"<td>{c['seller_density']:g}</td><td>{c['dawn_sku']}</td></tr>"
        for c in cand)
    rows2 = "".join(
        f"<tr><td>{r['item']}</td><td>{r['sku']:,}</td><td>{r['reviews']}</td></tr>"
        for r in s["rows"])

    return f"""<section class="act">
<h2>3막 · MD라면 무엇을 할 것인가</h2>
<div class="prose">
<p>진열을 걷어내는 방향은 택하지 않았다. 브랜드사와의 관계를 건드리는 데 비해
얻는 것이 분명하지 않기 때문이다. 대신 <strong>작동하는 조합을 늘리고,
타이밍을 만드는</strong> 쪽으로 세 가지를 제안한다.</p>

<h3>① 샛별 확대 — 증명된 조합을 인접 품목으로</h3>
<p>후보는 이미 정해져 있다. 판매자배송 안에서 리뷰밀도가 상위인데
샛별 SKU 가 0개인 품목이다. 비교하자면 판매자배송 기준으로 상의 {top_density:g} ·
하의 {bottom_density:g} · 아우터 {outer_density:g}이다.</p>
</div>
<div class="scroller"><table>
<thead><tr><th>품목</th><th>판매자 SKU</th><th>SKU당 리뷰</th><th>샛별 SKU</th></tr></thead>
<tbody>{rows1}</tbody></table></div>
<div class="prose">
<p>이 이동의 결과는 이미 관측됐다. 실내화는 {lift['실내화']['seller_density']:g}에서
{lift['실내화']['dawn_density']:g}까지({round(lift['실내화']['multiple'])}배),
학용품은 {lift['학용품']['seller_density']:g}에서
{lift['학용품']['dawn_density']:g}까지({round(lift['학용품']['multiple'])}배) 올랐다.
추측이 아니라 같은 카탈로그 안에서 확인된 패턴의 복제다.</p>

<h3>② 시즌·이벤트 기획전 — 진열은 그대로, 타이밍을 만든다</h3>
<p>카탈로그의 {s['sku_share']}%가 애초에 상시 구매재가 아니다.
설·생일·여름·간절기에 사는 물건을 상시 진열로만 두면 발견될 창이 없다.
상품이 나쁜 게 아니라 타이밍이 없는 것이고, 이건 MD가 기획전으로 직접 푸는 문제다.</p>
</div>
<div class="scroller"><table>
<thead><tr><th>품목</th><th>SKU</th><th>리뷰</th></tr></thead>
<tbody>{rows2}
<tr><td><b>합계</b></td><td><b>{s['total_sku']:,}</b> ({s['sku_share']}%)</td>
<td><b>{s['total_reviews']}</b> ({s['review_share']}%)</td></tr>
</tbody></table></div>
<div class="prose">
<h3>③ 장보기 동선 연계 — 이미 증명된 포지션의 확장</h3>
<p>키즈웨어에서 실제로 팔린 건 실내화와 학용품, 즉 생활 소모품이다.
성인 패션 리뷰 분석에서 언더웨어·홈웨어가 리뷰의 54%를 차지했던 것과 같은 행동이
키즈에서도 반복된다. 컬리 고객은 키즈웨어를 '외출복'이 아니라
<strong>'장보는 김에 사는 것'</strong>으로 다루고 있다.
신학기 장보기 동선에 붙이는 것이 저항이 가장 적은 확장 경로다.</p>
</div>
</section>
"""


def render_appendix(p):
    m = p["meta"]
    return f"""<section class="act">
<h2>부록 · 방법론과 한계</h2>
<div class="prose">
<p>카테고리 172(키즈웨어)와 919017(유아동패션)의 전 상품을 목록 API 로 수집한 뒤
상세 API 로 리뷰수를 재확인했다. 스냅샷은 {_snapshot_date(m['snapshot'])}이며 {m['n_sku']:,} SKU 다.</p>
<ul>
<li><b>리뷰수는 판매량의 대리지표다.</b> 노출기간·판매기간을 보정하지 않아
신상품에 불리하다. 순위를 판매량 순위로 읽으면 안 된다.</li>
<li><b>목록 API 의 리뷰수에 결함이 있다.</b> 리뷰가 적은 상품을 0 으로 반환한다.
목록에서 0 이던 3,596건을 상세 API 로 재확인해 555건을 보정했고,
총 리뷰수가 1,420 → {m['n_reviews']:,}건으로 늘었다. 이 문서의 모든 수치는 보정 후 값이다.</li>
<li><b>평점은 쓰지 않았다.</b> 컬리 API 가 rating/score/star 를 제공하지 않아
평점 컬럼이 전 행 비어 있다. 이 분석은 평점에 의존하지 않는다.</li>
<li><b>브랜드명은 상품명의 [브랜드] 접두사에서 추출했다</b>(커버리지 100%).
표본 20건을 상세 API 의 brand_info 와 대조해 17건 일치, 1건 표기차,
2건은 API 에만 브랜드가 없었다.</li>
<li><b>172 와 919017 은 별개 매장으로 봐야 한다.</b> 브랜드 교집합 0개(자카드 0.0000),
상품ID 교집합 0건이다. 172 는 level 1 독립 트리, 919017 은 level 2 로
분류 체계 자체가 다르다.</li>
<li><b>'기타' {(next(c['sku'] for c in p['category'] if c['item'] == '기타')):,}건은
분류 실패가 아니다.</b> 12개 주요 분류에 속하지 않는 품목이며 한복·파티용품 등이
여기 들어간다. 다만 '미상' 402건은 영문 모델명 위주로, 키워드 분류의 한계에 해당한다.</li>
</ul>
</div>
</section>
"""


def render_html(payload):
    parts = [render_head(payload), render_poster(payload),
             render_act1(payload), render_act2(payload),
             render_act3(payload), render_appendix(payload)]
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
