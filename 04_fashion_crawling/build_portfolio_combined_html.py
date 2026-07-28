# -*- coding: utf-8 -*-
"""통합 포트폴리오 HTML 템플릿 — build_portfolio_combined.render()가 호출.

CSS/레이아웃은 기존 output/portfolio.html 디자인 시스템을 그대로 유지하고,
본문 수치는 통계 dict(S)와 차트 dict(charts)에서 주입한다.
"""

HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>컬리 × 무신사 — 패션 이커머스 데이터 분석</title>
<style>
  :root {
    --ground: #fcfcfb; --panel: #f5f5f1; --ink: #0b0b0b; --secondary: #52514e;
    --muted: #898781; --hairline: #e1e0d9; --hairline-strong: #c3c2b7;
    --blue: #2a78d6; --blue-soft: #e8f0fb; --red: #e34948; --red-soft: #fceceb;
    --kurly: #5f0080; --kurly-soft: #f3e9f7; --chart-frame: transparent; --chart-bg: #fcfcfb;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --ground: #171613; --panel: #201f1b; --ink: #f0efe9; --secondary: #b5b3ab;
      --muted: #85837b; --hairline: #34322c; --hairline-strong: #4a4840;
      --blue: #6aa5e8; --blue-soft: #1d2a3c; --red: #ef7a79; --red-soft: #3a2222;
      --kurly: #c78ae0; --kurly-soft: #33203d; --chart-frame: #e1e0d9; --chart-bg: #fcfcfb;
    }
  }
  :root[data-theme="dark"] {
    --ground: #171613; --panel: #201f1b; --ink: #f0efe9; --secondary: #b5b3ab;
    --muted: #85837b; --hairline: #34322c; --hairline-strong: #4a4840;
    --blue: #6aa5e8; --blue-soft: #1d2a3c; --red: #ef7a79; --red-soft: #3a2222;
    --kurly: #c78ae0; --kurly-soft: #33203d; --chart-frame: #e1e0d9; --chart-bg: #fcfcfb;
  }
  :root[data-theme="light"] {
    --ground: #fcfcfb; --panel: #f5f5f1; --ink: #0b0b0b; --secondary: #52514e;
    --muted: #898781; --hairline: #e1e0d9; --hairline-strong: #c3c2b7;
    --blue: #2a78d6; --blue-soft: #e8f0fb; --red: #e34948; --red-soft: #fceceb;
    --kurly: #5f0080; --kurly-soft: #f3e9f7; --chart-frame: transparent; --chart-bg: #fcfcfb;
  }
  html { background: var(--ground); }
  body {
    margin: 0; background: var(--ground); color: var(--ink);
    font-family: "Pretendard Variable", Pretendard, "Apple SD Gothic Neo",
      "Noto Sans KR", "Malgun Gothic", system-ui, sans-serif;
    font-size: 16px; line-height: 1.72; -webkit-font-smoothing: antialiased;
  }
  .page { max-width: 860px; margin: 0 auto; padding: 56px 24px 80px; }
  .prose { max-width: 72ch; }
  a { color: var(--blue); text-decoration-thickness: 1px; text-underline-offset: 3px; }
  a:focus-visible, button:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
  .eyebrow { font-size: 12px; letter-spacing: 0.14em; color: var(--muted); font-weight: 600; margin: 0 0 14px; }
  h1 { font-size: clamp(30px, 5.4vw, 44px); line-height: 1.22; letter-spacing: -0.022em;
    font-weight: 800; margin: 0 0 18px; text-wrap: balance; }
  .thesis { font-size: clamp(17px, 2.4vw, 20px); line-height: 1.6; color: var(--secondary);
    margin: 0 0 28px; max-width: 60ch; text-wrap: balance; }
  .thesis strong { color: var(--ink); font-weight: 700; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 22px; }
  .chip { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 700;
    padding: 5px 13px; border-radius: 999px; border: 1px solid var(--hairline-strong); }
  .chip .dot { width: 8px; height: 8px; border-radius: 50%; }
  .chip-musinsa .dot { background: var(--ink); }
  .chip-kurly .dot { background: var(--kurly); }
  .chip-status { color: var(--secondary); font-weight: 600; border-style: dashed; }
  .meta { display: flex; flex-wrap: wrap; gap: 8px 28px; padding: 14px 0;
    border-top: 1px solid var(--hairline); border-bottom: 1px solid var(--hairline);
    font-size: 13.5px; color: var(--secondary); }
  .meta b { color: var(--ink); font-weight: 700; }
  .meta span { white-space: nowrap; }
  .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1px;
    background: var(--hairline); border: 1px solid var(--hairline); border-radius: 10px;
    overflow: hidden; margin: 36px 0 0; }
  .kpi { background: var(--panel); padding: 18px 18px 15px; }
  .kpi .v { font-size: 26px; font-weight: 800; letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums; line-height: 1.15; }
  .kpi .v small { font-size: 15px; font-weight: 700; color: var(--secondary); }
  .kpi .k { font-size: 12.5px; color: var(--muted); margin-top: 4px; }
  .kpi-risk .v { color: var(--red); }
  section { margin-top: 72px; }
  .sec-head { display: flex; align-items: baseline; gap: 14px; border-top: 2px solid var(--ink);
    padding-top: 14px; margin-bottom: 6px; }
  .sec-no { font-size: 13px; font-weight: 800; color: var(--blue);
    font-variant-numeric: tabular-nums; letter-spacing: 0.06em; }
  h2 { font-size: 23px; font-weight: 800; letter-spacing: -0.015em; margin: 0; text-wrap: balance; }
  .sec-sub { color: var(--muted); font-size: 14px; margin: 2px 0 0; }
  h3.claim { font-size: 17.5px; font-weight: 800; letter-spacing: -0.01em; margin: 26px 0 8px; text-wrap: balance; }
  h3.claim .hl { box-shadow: inset 0 -0.45em var(--blue-soft); }
  h3.claim .hl-risk { box-shadow: inset 0 -0.45em var(--red-soft); }
  ul { margin: 10px 0 0; padding-left: 20px; }
  li { margin: 6px 0; }
  li::marker { color: var(--muted); }
  .prose p { margin: 12px 0; }
  figure { margin: 26px 0 0; }
  .fig-panel { background: var(--chart-bg); border: 1px solid var(--hairline);
    outline: 1px solid var(--chart-frame); border-radius: 10px; padding: 10px 12px 6px; overflow-x: auto; }
  figure img { display: block; width: 100%; max-width: 900px; height: auto; margin: 0 auto; }
  figcaption { font-size: 12.5px; color: var(--muted); margin-top: 8px; padding-left: 2px; }
  .tbl-wrap { overflow-x: auto; margin-top: 18px; }
  table { border-collapse: collapse; width: 100%; font-size: 14px; line-height: 1.55; }
  th, td { text-align: left; padding: 9px 14px 9px 0; border-bottom: 1px solid var(--hairline); vertical-align: top; }
  th { font-size: 12px; letter-spacing: 0.07em; color: var(--muted); font-weight: 700;
    border-bottom: 1px solid var(--hairline-strong); white-space: nowrap; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  td:last-child, th:last-child { padding-right: 0; }
  .risk { color: var(--red); font-weight: 800; }
  .tbl-note { font-size: 12.5px; color: var(--muted); margin-top: 8px; }
  ol.insights { margin: 22px 0 0; padding: 0; list-style: none; counter-reset: ins; }
  ol.insights li { counter-increment: ins; display: grid; grid-template-columns: 34px 1fr;
    gap: 14px; padding: 15px 0; border-bottom: 1px solid var(--hairline); margin: 0; }
  ol.insights li::before { content: counter(ins); font-weight: 800; font-size: 15px; color: var(--blue);
    font-variant-numeric: tabular-nums; border-top: 2px solid var(--blue); padding-top: 2px; height: fit-content; }
  ol.insights b { font-weight: 800; }
  .callout { margin-top: 26px; border-left: 3px solid var(--blue); background: var(--panel);
    border-radius: 0 10px 10px 0; padding: 16px 20px; }
  .callout .tag { font-size: 11.5px; font-weight: 800; letter-spacing: 0.12em; color: var(--blue); }
  .callout p { margin: 6px 0 0; font-size: 15px; }
  .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 28px; margin-top: 20px; }
  .cols h4 { font-size: 14px; font-weight: 800; margin: 0 0 4px; }
  .cols ul { font-size: 13.5px; color: var(--secondary); }
  footer { margin-top: 80px; padding-top: 18px; border-top: 1px solid var(--hairline);
    font-size: 13px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 6px 24px; justify-content: space-between; }
</style>
</head>
<body>
"""

CAP = ('text-align:left; font-size:12px; letter-spacing:0.07em; '
       'color:var(--muted); font-weight:700; padding-bottom:10px;')
CODE = 'font-size:12px'


def _fig(src, alt, caption):
    return (f'    <figure>\n'
            f'      <div class="fig-panel"><img src="{src}" alt="{alt}"></div>\n'
            f'      <figcaption>{caption}</figcaption>\n'
            f'    </figure>\n')


def _comparison_callout(comp):
    if not comp or not comp.get("enabled"):
        return ""
    return f"""    <div class="callout" style="border-left-color:var(--kurly);">
      <span class="tag" style="color:var(--kurly);">📌 재현성 점검 · {comp['old_label']} → {comp['new_label']}</span>
      <p>같은 분석을 약 20일 뒤 다시 수집해 대조했다.
      <b>구조적 지표는 안정</b> — 무신사 평점 4점 이상 비중 {comp['m_4plus_old']}%→{comp['m_4plus_new']}%,
      컬리 169 레저/홈웨어의 25%+ 할인 비율 {comp['k169_25_old']}%→{comp['k169_25_new']}%로 상시할인 문법이 그대로 유지된다.
      표본이 무신사 {100 - comp['m_persist']}%·컬리 평균 {100 - comp['k_persist']}%나 교체됐는데도 결론이 흔들리지 않는다는 건,
      이 발견들이 그날의 노이즈가 아니라 <b>구조적 현상</b>이라는 방증이다.</p>
      <p style="margin-top:10px;"><b>전술적 지표는 이동</b> — 컬리 패션잡화(166)는 20일간 유지된 같은 상품 {comp['k166_keep_n']}개
      기준으로도 할인율 중앙값이 {comp['k166_disc_old']}%→{comp['k166_disc_new']}%로 올랐다.
      고단가 잡화가 정가 신뢰 기조에서 여름 시즌오프 프로모션으로 이동하는 신호다.
      <span style="color:var(--muted);">— 20일·단일 간격이라 추세가 아닌 두 시점 대조로 해석.</span></p>
    </div>
"""


def render(S, C, kw, date, comp=None):
    won = lambda n: f"{n:,}"
    k169_list0_pct = round(S["k169_list0"] / S["k169_n"] * 100)
    k169_disc_cnt = S["k169_n"] - S["k169_list0"]
    kw_str = "·".join(kw[:4]) if kw else "착용감·사이즈·소재"

    body = f"""
<div class="page">
  <header>
    <p class="eyebrow">커머스 데이터 분석 포트폴리오 — 04 · 패션 이커머스</p>
    <h1>컬리 × 무신사<br>크롤링부터 EDA까지, 패션 커머스 데이터 분석</h1>
    <p class="thesis">별점이 없는 컬리는 무엇으로 상품을 변별하는가 —
      <strong>거의 전량 상시할인(정가 {k169_list0_pct}%), 소수 브랜드 큐레이션, 상위 10% 상품에 쏠린 리뷰</strong>.
      컬리 패션 카테고리의 머천다이징 구조를 직접 수집한 데이터로 읽고,
      별점이 있는 무신사를 벤치마크 삼아 검증했다.</p>
    <div class="chips">
      <span class="chip chip-kurly"><span class="dot"></span>컬리 · 패션잡화 166 · 레저/홈웨어 169</span>
      <span class="chip chip-musinsa"><span class="dot"></span>무신사 · 속옷/홈웨어 026</span>
      <span class="chip chip-status">Python · pandas · matplotlib · Gradio</span>
    </div>
    <div class="meta">
      <span>유형 <b>개인 프로젝트 (커머스 MD)</b></span>
      <span>수집일 <b>{date}</b></span>
      <span>표본 <b>상품 232 (컬리 192 · 무신사 40) · 리뷰 {won(S['m_rev_n'])}건</b></span>
      <span>산출물 <b>크롤러 2종 · EDA 노트북 2종 · 대시보드</b></span>
    </div>

    <div class="kpis">
      <div class="kpi kpi-risk"><div class="v">{S['k169_list0']}<small>개</small></div><div class="k">컬리 레저/홈웨어 정가 판매 상품 (96개 중)</div></div>
      <div class="kpi kpi-risk"><div class="v">{S['k169_disc_med']}<small>%</small></div><div class="k">컬리 레저/홈웨어 할인율 중앙값 — 무신사의 {S['k_over_m_disc']}배</div></div>
      <div class="kpi"><div class="v">{S['m_4plus_pct']}<small>%</small></div><div class="k">무신사 4점 이상 리뷰 비중 — 평점 인플레이션</div></div>
      <div class="kpi kpi-risk"><div class="v">{S['m_finish_ratio']}<small>×</small></div><div class="k">무신사 저평점에서 뛰는 '마감/품질' 언급률</div></div>
    </div>
  </header>

  <section>
    <div class="sec-head"><span class="sec-no">개요</span><h2>수집 → 분석 → 대시보드 파이프라인</h2></div>
    <div class="prose">
      <p>공개 API가 없는 두 채널의 상품·리뷰 데이터를 크롤러 2종
      (<code>kurly_crawler.py</code> · <code>musinsa_crawler.py</code>)으로 직접 수집하고
      — 내부 API 리버스엔지니어링, 요청 간 1.5~3초 딜레이, 차단 시 즉시 중단 —
      채널별 데이터 구조에 맞춰 설계한 EDA 노트북과 Gradio 비교 대시보드(<code>app.py</code>)로
      연결했다. 컬리는 별점·브랜드 필드가 없는 구조라 수집과 분석 설계 모두
      무신사와 다르게 풀어야 했다.</p>
    </div>
    <div class="tbl-wrap">
      <table>
        <caption style="{CAP}">채널별 수집 설계 — 같은 스키마, 다른 엔지니어링</caption>
        <thead><tr><th>설계 포인트</th><th>컬리</th><th>무신사</th></tr></thead>
        <tbody>
          <tr><td>데이터 소스</td><td>내부 API + HTML <code style="{CODE}">__NEXT_DATA__</code> 폴백</td><td>내부 API (<code style="{CODE}">plp/goods</code>, 리뷰 API)</td></tr>
          <tr><td>인증</td><td>게스트 Bearer 토큰 (401 대응 절차 문서화)</td><td>불필요</td></tr>
          <tr><td>리뷰 페이지네이션</td><td>커서(<code style="{CODE}">after</code>) 방식</td><td>페이지 번호</td></tr>
          <tr><td>별점</td><td>없음 → 리뷰수 집중도(파레토)로 대체</td><td>있음 → 평점 분석</td></tr>
          <tr><td>브랜드 필드</td><td>미제공 → 상품명 <code style="{CODE}">[브랜드]</code> 패턴 추출</td><td>API 제공</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">01</span><h2>컬리 — 별점 없는 채널은 무엇으로 읽는가</h2></div>
    <p class="sec-sub">패션잡화(166) · 레저/홈웨어(169) 추천순 상위 각 96개 상품 · {date} 수집</p>
    <div class="prose">
      <p>컬리는 별점 제도가 없다. 그래서 평점 분석 대신 <b>리뷰수 집중도(파레토 곡선)로
      수요 쏠림을 측정</b>하고, 리뷰수 상한 표기(<code style="font-size:13px">999+</code>)는
      999로 치환하되 상한 도달 여부를 보존해 "실제 집중도는 이보다 높다"는 보수적
      추정으로 해석했다. 브랜드 필드도 제공되지 않아 상품명의
      <code style="font-size:13px">[브랜드]</code> 패턴에서 추출했다 —
      <b>데이터 구조가 다르면 분석 설계도 달라져야 한다</b>는 것이 이 절의 전제다.</p>
    </div>

    <div class="kpis">
      <div class="kpi kpi-risk"><div class="v">{S['k169_list0']}<small>개</small></div><div class="k">레저/홈웨어 정가 판매 상품 (96개 중)</div></div>
      <div class="kpi"><div class="v">{S['k169_disc_med']}<small>%</small></div><div class="k">레저/홈웨어 할인율 중앙값 — 무신사의 {S['k_over_m_disc']}배</div></div>
      <div class="kpi"><div class="v">{S['k166_top10share']}<small>%</small></div><div class="k">잡화 상위 10% 상품의 리뷰 점유율</div></div>
      <div class="kpi"><div class="v">{S['k169_brand_top_n']}<small>개</small></div><div class="k">레저/홈웨어 96개 중 단일 브랜드({S['k169_brand_top']}) 상품</div></div>
    </div>

{_fig(C['k169_price'], f"컬리 레저·홈웨어 추천 상위 96개 상품 가격 분포 히스토그램. 1~3만원대 집중, 중앙값 {won(S['k169_med'])}원.", f"컬리 레저/홈웨어(169) 가격 분포 — 점선은 중앙값 {won(S['k169_med'])}원")}{_fig(C['k169_disc'], "컬리 레저·홈웨어 할인율 분포 히스토그램. 40~50% 구간이 최빈, 0%(정가) 구간은 거의 비어 있음.", "컬리 레저/홈웨어(169) 할인율 분포 — 0%(정가) 구간이 거의 비어 있다")}    <div class="prose">
      <h3 class="claim"><span class="hl">레저/홈웨어: 정가 판매 {S['k169_list0']}개({k169_list0_pct}%)</span> — 컬리의 '정가'는 사실상 앵커 가격이다</h3>
      <ul>
        <li>가격 중앙값 {won(S['k169_med'])}원 — 같은 성격(속옷·홈웨어)인 무신사 026({won(S['m_med'])}원, 02절)보다
          한 단계 낮은 가격대다.</li>
        <li>96개 중 {k169_disc_cnt}개가 할인 중 — <b>{S['k169_25plus']}%가 25% 이상 할인</b>, 할인율 중앙값 {S['k169_disc_med']}%(최대 {S['k169_disc_max']}%).
          할인을 전제로 정가를 설계하는 카테고리로, 이 문법이 얼마나 극단적인지는
          07절에서 무신사와 나란히 비교한다.</li>
        <li>리뷰 0건 상품은 {S['k169_rev0']}/96. 상위 10% 상품이 리뷰의 {S['k169_top10share']}%를 점유하고
          리뷰수 상한(999+) 도달 상품 {S['k169_cap']}개 — 실제 집중도는 이보다 높다.</li>
      </ul>
    </div>

{_fig(C['k169_brand'], f"컬리 레저·홈웨어 브랜드별 진입 상품 수 가로 막대. {S['k169_brand_top']} {S['k169_brand_top_n']}개로 압도적, {S['k169_brand2']} {S['k169_brand2_n']}개 순.", "컬리 레저/홈웨어(169) 브랜드별 진입 상품 수 (2개 이상)")}    <div class="prose">
      <h3 class="claim"><span class="hl">한 브랜드가 96개 중 {S['k169_brand_top_n']}개</span> — 열린 마켓이 아니라 소수 브랜드 큐레이션</h3>
      <ul>
        <li>{S['k169_brand_top']}({S['k169_brand_top_n']}개)·{S['k169_brand2']}({S['k169_brand2_n']}개) 두 브랜드가 상위 노출의 절반을 차지.
          1개 상품만 올린 브랜드는 {S['k169_brand1cnt']}개다(무신사 026은 {S['m_brand1cnt']}개).</li>
        <li>컬리는 <b>입점 브랜드의 상품 라인을 통째로 반복 노출하는 큐레이션 구조</b>다.
          '많은 브랜드가 경쟁하고 PB가 볼륨을 가져가는' 무신사(04절)와 나란히 두면,
          같은 상품군이라도 채널의 머천다이징 문법이 완전히 다르다는 게 드러난다.</li>
      </ul>
    </div>

{_fig(C['k166_price'], f"컬리 패션잡화 추천 상위 96개 상품 가격 분포 히스토그램. 중앙값 {won(S['k166_med'])}원, 고가까지 넓게 분포.", f"컬리 패션잡화(166) 가격 분포 — 점선은 중앙값 {won(S['k166_med'])}원")}{_fig(C['k166_pareto'], f"컬리 패션잡화 리뷰수 파레토 곡선. 상위 10% 상품이 리뷰의 {S['k166_top10share']}%를 점유.", f"컬리 패션잡화(166) 리뷰수 파레토 곡선 — 상위 10% 상품이 리뷰의 {S['k166_top10share']}%")}    <div class="prose">
      <h3 class="claim"><span class="hl">잡화는 정반대</span> — 고단가 · 정가 중심, 수요는 소수 검증 상품에 집중</h3>
      <ul>
        <li>가격 중앙값 {won(S['k166_med'])}원(주얼리·슈즈·레인부츠) — 레저/홈웨어의 {S['k166_over_k169']}배.
          같은 채널 안에서도 카테고리별 가격 전략이 완전히 갈린다.</li>
        <li>정가 판매가 {S['k166_list0_pct']}%({S['k166_list0']}/96), 할인율 중앙값 {S['k166_disc_med']}% — 고단가 잡화는
          <b>할인보다 정가 신뢰에 무게를 둔 카테고리</b>.</li>
        <li>리뷰 0건 상품이 {S['k166_rev0_pct']}%({S['k166_rev0']}/96), 상위 10% 상품이 리뷰의 {S['k166_top10share']}%를 점유 —
          수요가 극소수 검증 상품에 몰려 있어 신규 진입 장벽이 높다.</li>
      </ul>
    </div>
    <div class="prose">
      <p>컬리의 수치가 '높은' 건지 판단하려면 기준점이 필요하다. 02~06절은 같은 틀
        (가격 · 할인 · 브랜드 구도 · 리뷰)을 별점과 리뷰 텍스트가 있는
        무신사 속옷/홈웨어(026)에 적용해 만든 <b>벤치마크</b>다 — 특히 05·06절은
        "별점이 있어도 결국 리뷰 본문을 읽어야 한다"는, 별점 없는 컬리에 그대로
        적용되는 결론으로 이어진다. 두 채널의 정량 비교는 07절에 정리했다.</p>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">02</span><h2>가격대 — 인기 상품은 어디에 몰려 있나</h2></div>
    <p class="sec-sub">컬리 비교 벤치마크 · 무신사 속옷/홈웨어(026) 인기순 상위 40개 상품 · {date} 스냅샷</p>
{_fig(C['m_price'], f"가격 분포 히스토그램. 1~5만원 구간에 상품이 집중되고 중앙값 {won(S['m_med'])}원 지점에 점선 표시. 오른쪽으로 긴 꼬리.", f"인기 상위 40개 상품 가격 분포 — 점선은 중앙값 {won(S['m_med'])}원")}    <div class="prose">
      <h3 class="claim"><span class="hl">1~5만원이 주력, 중앙값 {won(S['m_med'])}원</span> — 세트 상품이 우측 꼬리를 만든다</h3>
      <ul>
        <li>최저 {won(S['m_min'])}원 ~ 최고 {won(S['m_max'])}원. 평균({won(S['m_mean'])}원)이 중앙값보다 높은 오른쪽 꼬리 분포 —
          소수의 고가 세트 상품(브라+팬티 세트, 파자마 세트)이 평균을 끌어올린다.</li>
        <li>속옷/홈웨어는 아우터 대비 단가가 낮아, <b>세트 구성으로 객단가를 올리는 상품</b>이 상위권에 다수 포진.</li>
      </ul>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">03</span><h2>할인 구조 — '정가'는 진짜 가격인가</h2></div>
    <p class="sec-sub">컬리 비교 벤치마크 · 무신사 속옷/홈웨어(026)</p>
{_fig(C['m_disc'], "할인율 분포 히스토그램. 0~80% 구간, 20~40% 할인 구간이 두텁다.", f"할인율 분포 — 정가 판매(0%)는 40개 중 {S['m_list0']}개")}    <div class="prose">
      <h3 class="claim"><span class="hl">{S['m_25plus']}%가 25% 이상 할인</span> — 상시할인이 기본 구조다</h3>
      <ul>
        <li>정가 판매는 40개 중 {S['m_list0']}개({S['m_list0_pct']}%). 할인율 중앙값 {S['m_disc_med']}%, 최대 {S['m_disc_max']}%.</li>
        <li>'정가'는 사실상 앵커 가격으로 기능한다. <b>채널 간 가격 비교는 표시 할인율이 아니라
          실판매가 기준</b>이어야 한다는 근거.</li>
      </ul>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">04</span><h2>브랜드 구도 — 누가 카테고리를 지배하나</h2></div>
    <p class="sec-sub">컬리 비교 벤치마크 · 무신사 속옷/홈웨어(026) — 01절 큐레이션 구조와 대비되는 지점</p>
{_fig(C['m_brand'], f"브랜드별 상위 40위 내 진입 상품 수 가로 막대. {S['m_brand_top']} {S['m_brand_top_n']}개, {', '.join(S['m_brand_next'])} 순.", "인기 상위 40위 내 진입 상품 수 (2개 이상 브랜드)")}{_fig(C['m_scatter'], "리뷰수(로그 스케일) 대 평점 산점도. 무신사 스탠다드 계열이 리뷰수 압도적 우위, 평점은 대부분 4.5~5.0에 밀집.", f"리뷰 수(누적 판매 프록시) × 평점 — 리뷰가 있는 {S['m_prod_with_rating']}개 상품")}    <div class="prose">
      <h3 class="claim"><span class="hl">진입 폭은 글로벌 브랜드, 판매 볼륨은 PB</span> — 이원 구조</h3>
      <ul>
        <li>진입 상품 수는 {S['m_brand_top']}({S['m_brand_top_n']}개), {', '.join(S['m_brand_next'])} 순 —
          라이선스/글로벌 스포츠 언더웨어가 상위권을 넓게 점유.</li>
        <li>리뷰 수 기준으로는 {S['m_vol_top'][0][0]}({won(S['m_vol_top'][0][1])}건)·{S['m_vol_top'][1][0]}({won(S['m_vol_top'][1][1])}건)가 압도적 —
          진입 상품 수는 적지만 <b>개별 상품의 판매 볼륨은 PB가 지배</b>한다.</li>
        <li>평점은 리뷰 수와 무관하게 4.5~5.0에 몰려 있다 → 다음 절의 질문으로 이어진다.</li>
      </ul>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">05</span><h2>평점 — 별점은 변별력이 있는가</h2></div>
    <p class="sec-sub">컬리 비교 벤치마크 · 무신사 리뷰 {won(S['m_rev_n'])}건 — 별점 없는 컬리를 해석하는 근거</p>
{_fig(C['m_rating'], f"리뷰 평점 분포 막대. 5점 {won(S['m_r5'])}건({S['m_r5_pct']}%), 4점 {won(S['m_r4'])}건({S['m_r4_pct']}%), 3점 이하 {S['m_r3down']}건({S['m_r3down_pct']}%).", f"수집 리뷰 {won(S['m_rev_n'])}건의 평점 분포")}    <div class="prose">
      <h3 class="claim"><span class="hl-risk hl">{S['m_4plus_pct']}%가 4점 이상</span> — 평점만으로는 상품을 변별할 수 없다</h3>
      <ul>
        <li>5점 {won(S['m_r5'])}건({S['m_r5_pct']}%), 4점 {won(S['m_r4'])}건({S['m_r4_pct']}%). 3점 이하는 {S['m_r3down']}건({S['m_r3down_pct']}%)에 불과.</li>
        <li>상품 단위 평점도 리뷰가 있는 {S['m_prod_with_rating']}개 중 평균 {S['m_rating_mean']}, 최저 {S['m_rating_min']}으로 상향 압축 —
          전형적인 <b>평점 인플레이션</b>.</li>
        <li>결론: 이 카테고리에서 정보 가치는 별점이 아니라 <b>리뷰 본문, 특히 소수의 저평점 리뷰</b>에 있다
          — 별점이 아예 없는 컬리에서 리뷰 본문 마이닝이 필수인 이유이기도 하다.</li>
      </ul>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">06</span><h2>리뷰 텍스트 — 무엇에 만족하고 무엇에 불만인가</h2></div>
    <p class="sec-sub">컬리 비교 벤치마크 · 무신사 리뷰 {won(S['m_rev_n'])}건 — 컬리 리뷰 텍스트 분석의 설계 원형</p>
{_fig(C['m_keywords'], f"고평점 리뷰 빈출 키워드 가로 막대. {kw_str} 등이 상위.", "고평점(4~5점) 리뷰 빈출 키워드 — 간단 토큰화 + 불용어 제거")}    <div class="prose">
      <p>만족의 언어는 <b>착용감 · 사이즈 · 계절성(여름) · 소재 · 디자인</b>으로 요약된다.
      수집 시점(7월)과 맞물린 '여름 시원함' 언급이 상위권 — 시즌성이 강한 카테고리다.
      형태소 분석 없이 조사가 붙은 형태가 분리되는 한계는, 아래 속성 사전 기반 집계로 보완했다.</p>
    </div>
{_fig(C['m_aspects'], "속성별 언급률을 고평점과 저평점 리뷰로 나눠 비교한 막대. 마감/품질과 사이즈가 저평점에서 상승.", "속성 사전 기반 언급률 — 고평점(파랑) vs 저평점(빨강) 리뷰")}    <div class="prose">
      <h3 class="claim"><span class="hl-risk hl">저평점에서 튀는 속성이 곧 구매 리스크다</span></h3>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr><th>속성</th><th class="num">고평점 언급률</th><th class="num">저평점 언급률</th><th class="num">배율</th></tr>
        </thead>
        <tbody>
{_table_rows(S['table_rows'])}        </tbody>
      </table>
      <p class="tbl-note">저평점 표본 {S['m_lo_n']}건 — 수치는 방향성 해석 용도.</p>
    </div>
    <div class="prose">
      <ul>
        <li><b>마감/품질</b>(실밥, 봉제)이 저평점에서 언급률이 가장 크게 뛴다 — 불만의 핵심 동인.</li>
        <li><b>사이즈</b>는 만족 리뷰에서도 많이 언급되지만(정보 공유 목적), 저평점에서는
          '작게 나옴', '컵이 안 맞음' 같은 실패 경험으로 등장.</li>
        <li><b>배송</b>은 저평점에서 0% — 무신사 물류에 대한 불만은 사실상 없다.
          불만은 전적으로 상품 자체에서 발생한다.</li>
        <li>이 속성 사전 기반 집계 프레임은 <b>별점 없는 컬리 리뷰 텍스트 분석의 설계 원형</b>이 된다 —
          별점 대신 '불편·아쉽·별로' 같은 부정 표현과 동시 등장하는 속성을 집계하는 방식.</li>
      </ul>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">07</span><h2>채널 비교 — 컬리 vs 무신사</h2></div>
    <div class="prose">
      <p>같은 '홈웨어' 성격의 카테고리를 나란히 두면 컬리의 할인 문법이 얼마나 극단적인지,
        그리고 표시 할인율은 채널마다 문법이 달라 그 자체로는 비교 지표가 될 수 없다는
        점이 드러난다.</p>
    </div>
    <div class="tbl-wrap">
      <table>
        <caption style="{CAP}">채널 × 카테고리 비교 — 표시 할인율은 비교 지표가 될 수 없다</caption>
        <thead>
          <tr><th>지표</th><th class="num">컬리 169 레저/홈웨어</th><th class="num">컬리 166 패션잡화</th><th class="num">무신사 026 속옷/홈웨어</th></tr>
        </thead>
        <tbody>
          <tr><td>표본</td><td class="num">추천순 96개</td><td class="num">추천순 96개</td><td class="num">인기순 40개</td></tr>
          <tr><td>가격 중앙값</td><td class="num">{won(S['k169_med'])}원</td><td class="num">{won(S['k166_med'])}원</td><td class="num">{won(S['m_med'])}원</td></tr>
          <tr><td>정가 판매 비중</td><td class="num risk">{k169_list0_pct}%</td><td class="num">{S['k166_list0_pct']}%</td><td class="num">{S['m_list0_pct']}%</td></tr>
          <tr><td>할인율 중앙값</td><td class="num risk">{S['k169_disc_med']}%</td><td class="num">{S['k166_disc_med']}%</td><td class="num">{S['m_disc_med']}%</td></tr>
          <tr><td>25%+ 할인 비중</td><td class="num risk">{S['k169_25plus']}%</td><td class="num">{S['k166_25plus']}%</td><td class="num">{S['m_25plus']}%</td></tr>
          <tr><td>수요 집중(상위 10% 리뷰 점유)</td><td class="num">{S['k169_top10share']}%</td><td class="num">{S['k166_top10share']}%</td><td class="num">—</td></tr>
        </tbody>
      </table>
      <p class="tbl-note">무신사는 인기순, 컬리는 추천순 표본이라 직접 비교는 방향성 해석 용도.
        같은 '홈웨어' 성격이라도 표시 할인율 문법이 채널·카테고리마다 달라,
        가격 비교는 실판매가 기준이어야 한다는 02·03장의 결론을 채널 간에서 재확인.</p>
    </div>
    <div class="prose">
      <p><b>남은 작업</b> — 컬리 리뷰 본문 텍스트 분석은 별도 프로젝트(리뷰 마이닝 →
      Semantic ID 대시보드)로 진행 중이다. 형태소 분석기 적용, 29CM·W컨셉으로 채널 확장이 다음 단계.</p>
    </div>
{_comparison_callout(comp)}  </section>

  <section>
    <div class="sec-head"><span class="sec-no">결론</span><h2>종합 인사이트</h2></div>
    <ol class="insights">
      <li><span><b>컬리 가격 문법</b> — 레저/홈웨어(169)는 정가 판매 {k169_list0_pct}%·할인율 중앙값 {S['k169_disc_med']}%의
        할인 전제 설계, 패션잡화(166)는 정가 비중 {S['k166_list0_pct']}%·할인 중앙값 {S['k166_disc_med']}% —
        같은 채널 안에서도 카테고리별 가격 전략이 완전히 갈린다.</span></li>
      <li><span><b>컬리 머천다이징</b> — 열린 마켓이 아니라 소수 브랜드 큐레이션
        ({S['k169_brand_top']}가 96개 중 {S['k169_brand_top_n']}개). 수요는 상위 10% 상품에 {S['k169_top10share']}~{S['k166_top10share']}% 집중 —
        리뷰 없는 신규 상품의 노출·신뢰 설계가 관건.</span></li>
      <li><span><b>채널 비교</b> — 같은 홈웨어 성격의 무신사 026은 정가 판매 {S['m_list0_pct']}%·할인 중앙값 {S['m_disc_med']}%로
        컬리(169)보다 온건한 할인 구조. 표시 할인율 문법이 채널마다 달라
        <b>채널 간 가격 비교는 실판매가 기준</b>이어야 한다.</span></li>
      <li><span><b>평점의 한계</b> — 별점이 있는 무신사조차 {round(S['m_4plus_pct'])}%가 4점 이상으로 변별력 없음.
        정보는 {S['m_r3down_pct']}%의 저평점 리뷰 본문에 있다 — 별점 없는 컬리에서
        리뷰 텍스트 마이닝이 선택이 아니라 필수인 이유.</span></li>
      <li><span><b>불만 구조</b> — (무신사 리뷰 벤치마크 기준) 마감/품질 이슈가 저평점의
        최대 동인(언급률 {S['m_finish_ratio']}배), 그 다음이 사이즈 실패. 배송 불만은 0 —
        불만은 물류가 아니라 상품 자체에서 발생한다.</span></li>
    </ol>
    <div class="callout">
      <span class="tag">MD 관점 시사점</span>
      <p>별점이 없는 컬리에서 상품 신호는 처음부터 리뷰 본문뿐이고, 별점이 있는 무신사조차
      결국 본문을 읽어야 했다. 상품 페이지가 해결해야 할 정보는 <b>'사이즈 실패 방지'</b>(상세 실측,
      컵 스펙)와 <b>'품질 신뢰'</b>(마감 클로즈업)이며, 리뷰 이벤트로 별점을 쌓는 접근은 변별력이
      없어 효과가 제한적이다 — 다음 단계로 컬리 리뷰 본문 텍스트 마이닝이 필요한 근거.</p>
    </div>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">원칙</span><h2>데이터 수집 윤리 · 분석의 한계</h2></div>
    <div class="cols">
      <div>
        <h4>수집 원칙</h4>
        <ul>
          <li>비상업 · 학습/포트폴리오 목적으로만 수집</li>
          <li>요청 간 1.5~3초 딜레이, 분석에 필요한 최소량만 수집</li>
          <li>원본 데이터(리뷰 원문 등)는 저장소·포트폴리오에 비공개 —
            공개 산출물에는 집계 통계·시각화만 게재</li>
          <li>리뷰어 신체정보·닉네임 등 개인정보성 데이터는 익명화</li>
          <li>사이트 차단(403/429) 시 수집 즉시 중단</li>
        </ul>
      </div>
      <div>
        <h4>이 분석의 한계</h4>
        <ul>
          <li>특정 시점({date}) 스냅샷, 인기순·추천순 상위 표본 — 계절(여름) 편향 존재</li>
          <li>리뷰는 '도움돼요'순 상위 표집 — 장문·정보성 리뷰로 편향</li>
          <li>저평점 리뷰 {S['m_lo_n']}건 — 속성 언급률은 방향성 참고용</li>
          <li>속옷 카테고리는 플랫폼이 리뷰어 신체정보를 마스킹해
            키/몸무게 기반 사이즈 분석 불가</li>
        </ul>
      </div>
    </div>
  </section>

  <footer>
    <span>ecommerce-data-analysis / 04_fashion_crawling</span>
    <span>수집·분석·시각화: Python (requests · pandas · matplotlib · Gradio)</span>
  </footer>
</div>

</body>
</html>
"""
    return HEAD + body


def _table_rows(rows):
    out = []
    for label, hv, lv, ratio in rows:
        rcls = ' class="num risk"' if label.startswith("마감/품질") else ' class="num"'
        rtxt = f"{ratio:.1f}×" if ratio else "—"
        out.append(
            f'          <tr><td>{label}</td><td class="num">{hv:.1f}%</td>'
            f'<td class="num">{lv:.1f}%</td><td{rcls}>{rtxt}</td></tr>')
    return "\n".join(out) + "\n"
