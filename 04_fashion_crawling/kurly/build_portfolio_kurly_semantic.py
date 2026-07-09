# -*- coding: utf-8 -*-
"""
5단계: 리뷰 마이닝 → Semantic ID 프로젝트를 독립 HTML 목업으로 만든다.

기존 output/portfolio.html의 디자인 시스템(CSS 변수·섹션 패턴)을 그대로 재사용하고,
output/report/의 차트 PNG를 base64로 인라인 임베드해 완전히 자기완결적인 단일 HTML
파일을 만든다 (외부 리소스 요청 없음 → 깃허브 Pages 등에서 그대로 열림).

산출물: output/kurly_semantic_id.html
"""

import base64
import html
import json
import os

import pandas as pd

DATA_DIR = "data"
REPORT_DIR = os.path.join("output", "report")
OUT_PATH = os.path.join("output", "kurly_semantic_id.html")


def b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def main():
    df = pd.read_csv(os.path.join(DATA_DIR, "kurly_attributes_coded.csv"))
    products = pd.read_csv(os.path.join(DATA_DIR, "kurly_product_semantic_ids.csv"))
    codebook = json.load(open(os.path.join(DATA_DIR, "codebook_kurly.json"), encoding="utf-8"))

    n_reviews = len(df)
    n_products = df["Product Name"].nunique()
    season_n = df["계절감"].notna().sum()
    hidden_n = (df["불만사유"].notna() & df["감성"].isin(["만족", "중립"])).sum()
    total_complaints = df["불만사유"].notna().sum()
    hidden_pct = round(hidden_n * 100 / total_complaints)

    charts = {
        "c1": b64(os.path.join(REPORT_DIR, "chart1_attribute_mentions.png")),
        "c2": b64(os.path.join(REPORT_DIR, "chart2_size_by_category.png")),
        "c3": b64(os.path.join(REPORT_DIR, "chart3_complaint_types.png")),
        "c4": b64(os.path.join(REPORT_DIR, "chart4_risk_products.png")),
    }

    risky = products[products["리뷰수"] >= 5].sort_values("불만비율", ascending=False).head(8)
    risky_rows = "\n".join(
        f'<tr><td>{html.escape(r["Product Name"][:34])}</td><td class="num">{r["리뷰수"]}</td>'
        f'<td class="num risk">{r["불만비율"]:.0%}</td><td><code>{html.escape(r["semantic_id"])}</code></td></tr>'
        for _, r in risky.iterrows()
    )

    # 코드북 예시 3개 축만 목업으로 보여줌 (전체는 codebook_kurly.json 참고)
    def cb_rows(axis):
        return " · ".join(f"{k}={v}" for k, v in codebook[axis].items())

    page_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>컬리 리뷰 마이닝 — 실착 속성 코드북 & Semantic ID</title>
<style>
  :root {{
    --ground: #fcfcfb; --panel: #f5f5f1; --ink: #0b0b0b; --secondary: #52514e;
    --muted: #898781; --hairline: #e1e0d9; --hairline-strong: #c3c2b7;
    --blue: #2a78d6; --blue-soft: #e8f0fb; --red: #e34948; --red-soft: #fceceb;
    --kurly: #5f0080; --kurly-soft: #f3e9f7; --chart-frame: transparent; --chart-bg: #fcfcfb;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --ground: #171613; --panel: #201f1b; --ink: #f0efe9; --secondary: #b5b3ab;
      --muted: #85837b; --hairline: #34322c; --hairline-strong: #4a4840;
      --blue: #6aa5e8; --blue-soft: #1d2a3c; --red: #ef7a79; --red-soft: #3a2222;
      --kurly: #c78ae0; --kurly-soft: #33203d; --chart-frame: #e1e0d9; --chart-bg: #fcfcfb;
    }}
  }}
  :root[data-theme="dark"] {{
    --ground: #171613; --panel: #201f1b; --ink: #f0efe9; --secondary: #b5b3ab;
    --muted: #85837b; --hairline: #34322c; --hairline-strong: #4a4840;
    --blue: #6aa5e8; --blue-soft: #1d2a3c; --red: #ef7a79; --red-soft: #3a2222;
    --kurly: #c78ae0; --kurly-soft: #33203d; --chart-frame: #e1e0d9; --chart-bg: #fcfcfb;
  }}
  :root[data-theme="light"] {{
    --ground: #fcfcfb; --panel: #f5f5f1; --ink: #0b0b0b; --secondary: #52514e;
    --muted: #898781; --hairline: #e1e0d9; --hairline-strong: #c3c2b7;
    --blue: #2a78d6; --blue-soft: #e8f0fb; --red: #e34948; --red-soft: #fceceb;
    --kurly: #5f0080; --kurly-soft: #f3e9f7; --chart-frame: transparent; --chart-bg: #fcfcfb;
  }}
  html {{ background: var(--ground); }}
  body {{
    margin: 0; background: var(--ground); color: var(--ink);
    font-family: "Pretendard Variable", Pretendard, "Apple SD Gothic Neo", "Noto Sans KR",
      "Malgun Gothic", system-ui, sans-serif;
    font-size: 16px; line-height: 1.72; -webkit-font-smoothing: antialiased;
  }}
  .page {{ max-width: 860px; margin: 0 auto; padding: 56px 24px 80px; }}
  .prose {{ max-width: 72ch; }}
  a {{ color: var(--blue); text-decoration-thickness: 1px; text-underline-offset: 3px; }}
  .eyebrow {{ font-size: 12px; letter-spacing: 0.14em; color: var(--muted); font-weight: 600; margin: 0 0 14px; }}
  h1 {{ font-size: clamp(30px, 5.4vw, 44px); line-height: 1.22; letter-spacing: -0.022em; font-weight: 800; margin: 0 0 18px; text-wrap: balance; }}
  .thesis {{ font-size: clamp(17px, 2.4vw, 20px); line-height: 1.6; color: var(--secondary); margin: 0 0 28px; max-width: 60ch; text-wrap: balance; }}
  .thesis strong {{ color: var(--ink); font-weight: 700; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 22px; }}
  .chip {{ display: inline-flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 700; padding: 5px 13px; border-radius: 999px; border: 1px solid var(--hairline-strong); }}
  .chip .dot {{ width: 8px; height: 8px; border-radius: 50%; }}
  .chip-kurly .dot {{ background: var(--kurly); }}
  .chip-status {{ color: var(--secondary); font-weight: 600; border-style: dashed; }}
  .meta {{ display: flex; flex-wrap: wrap; gap: 8px 28px; padding: 14px 0; border-top: 1px solid var(--hairline); border-bottom: 1px solid var(--hairline); font-size: 13.5px; color: var(--secondary); }}
  .meta b {{ color: var(--ink); font-weight: 700; }}
  .meta span {{ white-space: nowrap; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: var(--hairline); border: 1px solid var(--hairline); border-radius: 10px; overflow: hidden; margin: 36px 0 0; }}
  .kpi {{ background: var(--panel); padding: 18px 18px 15px; }}
  .kpi .v {{ font-size: 26px; font-weight: 800; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; line-height: 1.15; }}
  .kpi .v small {{ font-size: 15px; font-weight: 700; color: var(--secondary); }}
  .kpi .k {{ font-size: 12.5px; color: var(--muted); margin-top: 4px; }}
  .kpi-risk .v {{ color: var(--red); }}
  section {{ margin-top: 72px; }}
  .sec-head {{ display: flex; align-items: baseline; gap: 14px; border-top: 2px solid var(--ink); padding-top: 14px; margin-bottom: 6px; }}
  .sec-no {{ font-size: 13px; font-weight: 800; color: var(--blue); font-variant-numeric: tabular-nums; letter-spacing: 0.06em; }}
  h2 {{ font-size: 23px; font-weight: 800; letter-spacing: -0.015em; margin: 0; text-wrap: balance; }}
  .sec-sub {{ color: var(--muted); font-size: 14px; margin: 2px 0 0; }}
  h3.claim {{ font-size: 17.5px; font-weight: 800; letter-spacing: -0.01em; margin: 26px 0 8px; text-wrap: balance; }}
  h3.claim .hl {{ box-shadow: inset 0 -0.45em var(--blue-soft); }}
  h3.claim .hl-risk {{ box-shadow: inset 0 -0.45em var(--red-soft); }}
  ul {{ margin: 10px 0 0; padding-left: 20px; }}
  li {{ margin: 6px 0; }}
  li::marker {{ color: var(--muted); }}
  .prose p {{ margin: 12px 0; }}
  figure {{ margin: 26px 0 0; }}
  .fig-panel {{ background: var(--chart-bg); border: 1px solid var(--hairline); outline: 1px solid var(--chart-frame); border-radius: 10px; padding: 10px 12px 6px; overflow-x: auto; }}
  figure img {{ display: block; width: 100%; max-width: 900px; height: auto; margin: 0 auto; }}
  figcaption {{ font-size: 12.5px; color: var(--muted); margin-top: 8px; padding-left: 2px; }}
  .tbl-wrap {{ overflow-x: auto; margin-top: 18px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14px; line-height: 1.55; }}
  th, td {{ text-align: left; padding: 9px 14px 9px 0; border-bottom: 1px solid var(--hairline); vertical-align: top; }}
  th {{ font-size: 12px; letter-spacing: 0.07em; color: var(--muted); font-weight: 700; border-bottom: 1px solid var(--hairline-strong); white-space: nowrap; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  td:last-child, th:last-child {{ padding-right: 0; }}
  .risk {{ color: var(--red); font-weight: 800; }}
  .tbl-note {{ font-size: 12.5px; color: var(--muted); margin-top: 8px; }}
  code {{ font-family: ui-monospace, "SF Mono", Consolas, monospace; font-size: 12.5px; background: var(--panel); border: 1px solid var(--hairline); border-radius: 5px; padding: 1px 6px; }}
  .pipeline {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-top: 24px; }}
  .step {{ background: var(--panel); border: 1px solid var(--hairline); border-radius: 10px; padding: 16px 18px; }}
  .step .no {{ font-size: 11.5px; font-weight: 800; color: var(--blue); letter-spacing: 0.1em; }}
  .step h4 {{ margin: 6px 0 6px; font-size: 15.5px; font-weight: 800; }}
  .step p {{ margin: 0; font-size: 13.5px; color: var(--secondary); line-height: 1.6; }}
  .axis-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; margin-top: 20px; }}
  .axis-card {{ background: var(--panel); border: 1px solid var(--hairline); border-radius: 10px; padding: 14px 16px; }}
  .axis-card h4 {{ margin: 0 0 6px; font-size: 14px; font-weight: 800; }}
  .axis-card p {{ margin: 0; font-size: 12.5px; color: var(--secondary); line-height: 1.6; }}
  .callout {{ margin-top: 26px; border-left: 3px solid var(--blue); background: var(--panel); border-radius: 0 10px 10px 0; padding: 16px 20px; }}
  .callout .tag {{ font-size: 11.5px; font-weight: 800; letter-spacing: 0.12em; color: var(--blue); }}
  .callout p {{ margin: 6px 0 0; font-size: 15px; }}
  footer {{ margin-top: 80px; padding-top: 18px; border-top: 1px solid var(--hairline); font-size: 13px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 6px 24px; justify-content: space-between; }}
</style>
</head>
<body>
<div class="page">
  <header>
    <p class="eyebrow">커머스 데이터 분석 — 04 · 패션 이커머스 · 컬리</p>
    <h1>상세페이지는 '판매자의 언어',<br>리뷰는 '고객의 언어'다</h1>
    <p class="thesis">리뷰 {n_reviews:,}건에서 실착 속성을 뽑아 코드북을 만들고,
      상품마다 <strong>Semantic ID</strong>를 부여했다. 컬리는 별점이 없는
      플랫폼이라, 감성·불만사유 태그로 그 자리를 대신했다.</p>
    <div class="chips">
      <span class="chip chip-kurly"><span class="dot"></span>컬리 · 패션의류/신발잡화/언더웨어 3카테고리</span>
      <span class="chip chip-status">Python · pandas · Gemini API · matplotlib</span>
    </div>
    <div class="meta">
      <span>유형 <b>개인 프로젝트 (커머스 MD → AI 전환)</b></span>
      <span>표본 <b>상품 {n_products}개 · 리뷰 {n_reviews:,}건</b></span>
      <span>산출물 <b>속성 코드북 · 상품별 Semantic ID · 인사이트 리포트</b></span>
    </div>
    <div class="kpis">
      <div class="kpi"><div class="v">{n_products}</div><div class="k">Semantic ID 부여 상품 수</div></div>
      <div class="kpi"><div class="v">8</div><div class="k">추출 속성 축 (핏·사이즈감·계절감 등)</div></div>
      <div class="kpi kpi-risk"><div class="v">{hidden_pct}<small>%</small></div><div class="k">불만이 '만족/중립' 리뷰 속에 숨어 있는 비율</div></div>
      <div class="kpi kpi-risk"><div class="v">43<small>%</small></div><div class="k">최고 리스크 상품 불만비율</div></div>
    </div>
  </header>

  <section>
    <div class="sec-head"><span class="sec-no">개요</span><h2>리뷰 → 코드북 → Semantic ID 파이프라인</h2></div>
    <div class="pipeline">
      <div class="step"><span class="no">STEP 1</span><h4>속성 추출</h4><p>Gemini API로 리뷰 한 건마다 핏·사이즈감·계절감 등 8축을 JSON으로 구조화. 배치 25건씩, 총 62회 호출.</p></div>
      <div class="step"><span class="no">STEP 2</span><h4>코드북 구축</h4><p>축마다 값을 정규화(동의어 통합)하고 빈도순으로 번호를 매겨 <code>{{"핏":{{"1":"크롭",...}}}}</code> 형태로 저장.</p></div>
      <div class="step"><span class="no">STEP 3</span><h4>Semantic ID 부여</h4><p>상품 단위로 리뷰 속성의 최빈값을 모아 <code>사2-두1-신1-계1</code> 같은 대표 코드를 부여.</p></div>
      <div class="step"><span class="no">STEP 4</span><h4>MD 인사이트</h4><p>상세페이지엔 없는 정보, 반복 불만, 카테고리별 차이를 리포트로 정리.</p></div>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">01</span><h2>리뷰에서 가장 많이 오가는 화두는 무엇인가</h2></div>
    <p class="sec-sub">전체 {n_reviews:,}건 중 각 속성 축이 언급된 건수</p>
    <figure>
      <div class="fig-panel"><img src="data:image/png;base64,{charts['c1']}" alt="속성 언급 빈도 차트"></div>
      <figcaption>계절감이 {season_n}건으로 가장 많이 언급됨</figcaption>
    </figure>
    <div class="prose">
      <h3 class="claim"><span class="hl">계절감·착용상황이 가장 자주 오가는 화두</span> — 상세페이지에는 아이콘 한 줄뿐</h3>
      <p>상세페이지는 소재/사이즈표를 나열하는 데 집중하지만, 고객은 리뷰에서
        "이거 여름에 입기 좋아요", "데일리로 자주 입어요"처럼 실제 착용 맥락을
        가장 많이 이야기한다. 이 맥락 정보를 상세페이지 상단 요약에 반영하면
        구매 전 궁금증을 줄일 수 있다.</p>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">02</span><h2>카테고리별 사이즈감 — "여기는 크게 사야 하나요?"</h2></div>
    <figure>
      <div class="fig-panel"><img src="data:image/png;base64,{charts['c2']}" alt="카테고리별 사이즈감 분포 차트"></div>
      <figcaption>패션의류(165) · 신발잡화(166) · 언더웨어홈웨어(169) 비교</figcaption>
    </figure>
    <div class="prose">
      <h3 class="claim"><span class="hl-risk hl">언더웨어·홈웨어는 '작게 나옴' 언급이 가장 높음</span></h3>
      <p>같은 "사이즈감" 축이라도 카테고리마다 분포가 다르다. 언더웨어·홈웨어(169)는
        작게 나온다는 언급 비중이 세 카테고리 중 가장 높아, 사이즈 가이드 문구를
        보강할 우선순위가 높은 카테고리로 판단된다.</p>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">03</span><h2>좋은 평가 속에 숨은 불만</h2></div>
    <figure>
      <div class="fig-panel"><img src="data:image/png;base64,{charts['c3']}" alt="불만사유 유형 차트"></div>
      <figcaption>불만사유가 확인된 리뷰 {total_complaints}건의 유형 분포</figcaption>
    </figure>
    <div class="prose">
      <h3 class="claim"><span class="hl-risk hl">{hidden_pct}%는 전체 톤이 '만족/중립'인 리뷰 속 불만</span></h3>
      <p>컬리는 별점이 없는 플랫폼이라 "평점이 낮은 리뷰만 본다"는 전략 자체가
        불가능하다. 감성 태그로 필터링해도 마찬가지다 — 불만사유가 달린 리뷰의
        {hidden_pct}%는 리뷰 전체 톤이 '만족'이나 '중립'으로 분류된다. 결국
        <b>리뷰 본문을 실제로 읽거나 텍스트 마이닝을 해야만</b> 잡히는 신호라는 뜻이다.</p>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">04</span><h2>반품·CS 리스크 후보 상품</h2></div>
    <figure>
      <div class="fig-panel"><img src="data:image/png;base64,{charts['c4']}" alt="불만비율 TOP 10 상품 차트"></div>
      <figcaption>리뷰 5건 이상 상품 중 불만비율 TOP 10</figcaption>
    </figure>
    <div class="tbl-wrap">
      <table>
        <thead><tr><th>상품명</th><th class="num">리뷰수</th><th class="num">불만비율</th><th>Semantic ID</th></tr></thead>
        <tbody>
{risky_rows}
        </tbody>
      </table>
    </div>
    <p class="tbl-note">별점이 없어 산출 불가능한 지표를, 리뷰 문장에서 불만이 직접 언급된 비율로 대체해 만든 랭킹.</p>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">05</span><h2>Semantic ID — 코드북으로 상품을 요약하기</h2></div>
    <p class="sec-sub">축별 코드북 예시 (전체 8축 중 3개)</p>
    <div class="axis-grid">
      <div class="axis-card"><h4>핏</h4><p>{cb_rows('핏')}</p></div>
      <div class="axis-card"><h4>사이즈감</h4><p>{cb_rows('사이즈감')}</p></div>
      <div class="axis-card"><h4>계절감</h4><p>{cb_rows('계절감')}</p></div>
    </div>
    <div class="callout">
      <span class="tag">예시</span>
      <p><code>사2-두1-신1-착1-계1</code> = "사이즈는 크게 나오고, 얇고 신축성 좋은 원단이며,
        데일리로 여름에 입는 상품" — 리뷰가 없는 신규 입고 상품도, 코드북을 공유하는
        유사 상품의 Semantic ID를 참고해 추천·MD 태깅에 활용할 수 있다.</p>
    </div>
  </section>

  <footer>
    <span>데이터: 컬리 리뷰 {n_reviews:,}건 (패션의류 165 · 신발잡화 166 · 언더웨어홈웨어 169)</span>
    <span>속성 추출: Google Gemini API</span>
  </footer>
</div>
</body>
</html>
"""

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(page_html)
    print(f"저장 완료: {OUT_PATH} ({os.path.getsize(OUT_PATH) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
