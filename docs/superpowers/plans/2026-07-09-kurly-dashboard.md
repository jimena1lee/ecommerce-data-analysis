# 컬리 리뷰 인사이트 대시보드 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 컬리 리뷰 마이닝 데이터를 미리 계산해 심은 자기완결 정적 HTML 대시보드(탭 3개: 신상품 리뷰 미리보기 · 브랜드 프로필 · 연구 탐색 보드)를 생성하는 파이썬 빌드 스크립트를 만든다.

**Architecture:** `kurly/build_dashboard_kurly.py`가 `kurly/data/`의 CSV·JSON을 읽어 페이로드 dict를 계산하고, `kurly/dashboard_template.html`(CSS·JS 포함 UI 템플릿)의 `/*__PAYLOAD__*/` 자리에 JSON으로 주입해 `kurly/output/dashboard.html`을 생성한다. 런타임 서버·API 호출 없음. 모든 인터랙션(유사도 계산·차트)은 내장 JS가 클라이언트에서 수행.

**Tech Stack:** Python 3.10 + pandas (빌드), 순수 HTML/CSS/JS + 인라인 SVG 차트 (런타임, 외부 CDN 없음), pytest (페이로드 검증)

## Global Constraints

- 산출물 `kurly/output/dashboard.html`은 단일 파일·외부 리소스 요청 0건 (스펙: GitHub Pages·오프라인에서 열림)
- 모든 예측 UI에 "유사 상품 N개 · 리뷰 M건 기반" 상시 표기, 유사 상품 3개 미만이면 예측 대신 데이터 부족 안내 (스펙: 정직성 장치)
- 한국어 UI, 모바일(375px)에서 레이아웃 깨지지 않을 것
- 데이터 규모(상품 199개·리뷰 1,543건) 헤더/푸터에 명시
- 기존 파일 수정 금지 (README.md 한 곳 제외), 신규 파일만 추가
- UI 작업 시작 전에 frontend-design 스킬과 dataviz 스킬을 읽고 적용할 것

---

### Task 1: 페이로드 빌더 (`build_payload`) + pytest 검증

**Files:**
- Create: `kurly/build_dashboard_kurly.py`
- Create: `kurly/test_dashboard_payload.py`
- Modify: `04_fashion_crawling/requirements.txt` (pytest 추가)

**Interfaces:**
- Produces: `build_payload() -> dict` — 아래 스키마의 dict. `main()`은 Task 2에서 추가.
- 페이로드 스키마 (JS가 이 구조에 의존, Task 3~5의 계약):

```json
{
  "meta": {"built": "2026-07-09", "n_products": 199, "n_reviews": 1543,
           "cats": {"165": "패션의류", "166": "신발·잡화", "169": "언더웨어·홈웨어"}},
  "axes": ["핏","사이즈감","기장","비침","두께","신축성","착용상황","계절감"],
  "codebook": {"핏": ["크롭","루즈핏","오버핏","슬림","정핏"], "...": ["코드1 라벨","코드2 라벨"]},
  "products": [{
     "name": "상품명", "cat": "165", "brand": "브랜드", "price": 76834,
     "review_n": 10, "complaint_n": 1, "sid": "비2-착3-계1",
     "mentions": {"계절감": {"여름": 3}, "사이즈감": {"정사이즈": 2}},
     "samples": [{"t": "리뷰 본문 앞 140자", "sent": "만족", "reason": "사이즈 작음 또는 null"}]
  }],
  "brands": [{
     "name": "슬로우롤리", "n_products": 31, "n_reviews": 120, "avg_price": 45000,
     "complaint_rate": 0.08, "size": {"정사이즈": 12, "크게 나옴": 3, "작게 나옴": 1},
     "mentions": {"착용상황": {"데일리": 20}}, "reasons": [["사이즈 작음", 3]],
     "cats": ["165"],
     "products": [{"name": "…", "review_n": 10, "complaint_n": 1}]
  }],
  "cat_stats": {"165": {"n_products": 96, "n_reviews": 600, "complaint_rate": 0.12,
                "avg_price": 52000, "mentions": {"계절감": 90},
                "size": {"정사이즈": 40, "크게 나옴": 25, "작게 나옴": 0}}},
  "complaint_reasons": [["사이즈 작음", 27], ["배송 지연", 9]]
}
```

**계산 규칙 (구현 세부):**

1. 데이터 로드: `data/kurly_products_{165,166,169}_20260709.csv` 3개 concat 후 `_goods_no`로 dedupe(288→고유). `data/kurly_attributes_coded.csv`(리뷰 태깅), `data/kurly_product_semantic_ids.csv`(상품별 SID), `data/codebook_kurly.json`.
2. 상품 목록 = semantic_ids CSV의 199개. `Product Name`으로 products CSV와 left join해 Brand·Price 취득(검증 완료: 누락 0). Price는 `"76,834"` → int 파싱, 실패 시 None.
3. `mentions` = attributes_coded를 상품명으로 groupby, 8축 각각 라벨 value_counts를 dict로.
4. `samples` = 상품별 리뷰 최대 3건. 우선순위: 불만사유 있는 리뷰 → 속성 언급 많은 리뷰 → 나머지. `Review Body`는 140자 절단(말줄임 `…` 추가).
5. `brands` = 상품 3개 이상(join된 products 기준) 브랜드만. `complaint_rate` = 불만리뷰수 합 / 리뷰수 합 (semantic_ids의 리뷰수·불만리뷰수 컬럼 사용). `size`는 사이즈감 mentions 합산.
6. `complaint_reasons` = `build_insight_report_kurly.py`의 chart3 정규화 로직(사이즈 작음 계열 통합 등)을 그대로 복사·재사용해 상위 10개 + 나머지 `["기타(개별 불만)", n]`.
7. `cat_stats.complaint_rate` = 카테고리별 불만리뷰수 합/리뷰수 합, `mentions`는 축별 총 언급 수.

- [ ] **Step 1: pytest 설치 및 requirements 갱신**

```
pip install pytest
```

`requirements.txt` 맨 아래에 추가:
```
# Dashboard build 검증
pytest>=8.0
```

- [ ] **Step 2: 실패하는 테스트 작성** — `kurly/test_dashboard_payload.py`

```python
# -*- coding: utf-8 -*-
"""build_dashboard_kurly.build_payload() 불변식 검증 (kurly/ 에서 pytest 실행)."""
import pytest
from build_dashboard_kurly import build_payload


@pytest.fixture(scope="module")
def payload():
    return build_payload()


def test_meta_counts(payload):
    assert payload["meta"]["n_products"] == 199
    assert payload["meta"]["n_reviews"] == 1543


def test_products_complete(payload):
    assert len(payload["products"]) == 199
    for p in payload["products"]:
        assert p["cat"] in ("165", "166", "169")
        assert p["brand"]                      # join 누락 없음 (사전 검증됨)
        assert 0 <= p["complaint_n"] <= p["review_n"]
        assert len(p["samples"]) >= 1          # 코딩된 리뷰가 1건 이상인 상품만 목록에 있음


def test_underwear_size_matches_report(payload):
    # 기존 리포트: 언더웨어·홈웨어 '작게 나옴' 27% (±3%p 허용)
    size = payload["cat_stats"]["169"]["size"]
    total = sum(size.values())
    assert abs(size.get("작게 나옴", 0) / total - 0.27) < 0.03


def test_brands_min_products(payload):
    assert all(b["n_products"] >= 3 for b in payload["brands"])
    assert 25 <= len(payload["brands"]) <= 33   # 사전 확인값 29 근방


def test_top_complaint_reason(payload):
    assert payload["complaint_reasons"][0][0].startswith("사이즈")
```

- [ ] **Step 3: 실패 확인**

Run: `cd kurly && python -m pytest test_dashboard_payload.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_dashboard_kurly'`

- [ ] **Step 4: `build_dashboard_kurly.py`에 `build_payload()` 구현** (위 계산 규칙 1~7 그대로. 파일 헤더는 기존 `build_portfolio_kurly_semantic.py` 스타일의 한국어 docstring)

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd kurly && python -m pytest test_dashboard_payload.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add kurly/build_dashboard_kurly.py kurly/test_dashboard_payload.py requirements.txt
git commit -m "대시보드 페이로드 빌더 추가 (상품·브랜드·카테고리 통계 사전 계산)"
```

---

### Task 2: HTML 템플릿 셸 + 페이로드 주입 + 탭 내비게이션

**Files:**
- Create: `kurly/dashboard_template.html`
- Modify: `kurly/build_dashboard_kurly.py` (`main()` 추가)

**Interfaces:**
- Consumes: `build_payload()` (Task 1)
- Produces: `main()` — 템플릿의 `/*__PAYLOAD__*/` 문자열을 `const DATA = {json};`으로 치환해 `output/dashboard.html` 저장. 템플릿 전역 JS: `const DATA` 를 탭 3~5 코드가 참조. 탭 컨테이너 id: `#tab-predict`, `#tab-brand`, `#tab-explore`.

**작업 내용:**

1. **frontend-design 스킬과 dataviz 스킬을 먼저 읽는다** (Global Constraints). 디자인 방향: 컬리 톤 퍼플(#5f0080 계열)을 포인트로 한 라이트 UI, 기존 portfolio.html과 구별되는 "업무 툴" 느낌. 시스템 폰트 스택(Pretendard 폴백 포함, 외부 폰트 로드 금지).
2. 템플릿 구조: 헤더(타이틀 + 데이터 규모 명시 "컬리 패션 3개 카테고리 · 상품 199개 · 리뷰 1,543건 기반") → 탭 바(3버튼) → 탭 컨테이너 3개(내용은 Task 3~5에서 채움, 이 단계에선 자리표시 텍스트) → 푸터(파이프라인 한 줄 + 빌드 날짜).
3. 탭 전환 JS(클릭 시 `.active` 토글), 모바일 미디어쿼리(≤480px: 탭 가로 스크롤, 그리드 1열).
4. `main()`:

```python
def main():
    payload = build_payload()
    with open("dashboard_template.html", encoding="utf-8") as f:
        tpl = f.read()
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html_out = tpl.replace("/*__PAYLOAD__*/", "const DATA = " + js + ";")
    os.makedirs("output", exist_ok=True)
    with open(os.path.join("output", "dashboard.html"), "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"생성 완료: output/dashboard.html ({len(html_out)//1024} KB)")
```

- [ ] **Step 1: 템플릿 작성 (셸 + 탭 전환 + `/*__PAYLOAD__*/` 스크립트 블록)**
- [ ] **Step 2: `main()` 추가 후 빌드 실행** — Run: `cd kurly && python build_dashboard_kurly.py` / Expected: `생성 완료: output/dashboard.html`
- [ ] **Step 3: 브라우저 확인** — 탭 3개 전환 동작, 콘솔 에러 0건, `DATA.products.length === 199`
- [ ] **Step 4: Commit** — `git add kurly/dashboard_template.html kurly/build_dashboard_kurly.py && git commit -m "대시보드 템플릿 셸 + 페이로드 주입"` (output/dashboard.html은 배포 시점에 커밋)

---

### Task 3: 탭 1 — 신상품 리뷰 미리보기

**Files:**
- Modify: `kurly/dashboard_template.html` (`#tab-predict` 마크업 + JS)

**Interfaces:**
- Consumes: `DATA.products[].{cat,mentions,review_n,complaint_n,samples,sid,price}`, `DATA.cat_stats`, `DATA.codebook`, `DATA.axes`

**UI 구성 (좌 입력 / 우 결과, 모바일에선 상하):**

- 입력 패널: 카테고리 3택1(칩 버튼, 필수) / 속성 칩 그룹 — 계절감·두께·핏·신축성·착용상황 (각 축은 codebook 라벨을 칩으로, 축당 1개 선택·재클릭 해제) / 가격대 4택1 선택형(~2만원 / 2~4만원 / 4~7만원 / 7만원~, 선택 해제 가능)
- 결과 패널 5블록: ① 유사 상품 카드 리스트 ② 예상 리뷰 프로필(가로 막대 SVG) ③ 리스크 게이지 ④ MD 액션 제안 ⑤ 실제 리뷰 발췌
- 결과 상단에 항상: `유사 상품 {N}개 · 리뷰 {M}건 기반` 배지

**유사도 로직 (JS, 이 코드 그대로 사용):**

```js
const PRICE_BANDS = {a:[0,20000], b:[20000,40000], c:[40000,70000], d:[70000,Infinity]};

function findSimilar(cat, sel, band) {           // sel = {축: 라벨}
  const scored = DATA.products
    .filter(p => p.cat === cat)
    .map(p => {
      let score = 0; const matched = [];
      for (const [axis, label] of Object.entries(sel)) {
        const m = p.mentions[axis] || {};
        if (m[label]) { score += 2; matched.push(axis + ":" + label); }
      }
      if (band && p.price != null) {
        const [lo, hi] = PRICE_BANDS[band];
        if (p.price >= lo && p.price < hi) score += 1;
      }
      return { p, score, matched };
    })
    .filter(x => Object.keys(sel).length === 0 ? true : x.score > 0)
    .sort((a, b) => b.score - a.score || b.p.review_n - a.p.review_n);
  return scored.slice(0, 12);
}
```

**MD 액션 규칙 (유사 상품군 합산 mentions·불만율 기준, 매칭되는 것 전부 표시):**

| 조건 | 제안 문구 |
| --- | --- |
| 사이즈감 중 '작게 나옴' ≥ 25% | "이 조합은 '작게 나옴' 언급이 잦습니다. 상세페이지에 '실측보다 타이트한 편' 안내 권장" |
| 사이즈감 중 '크게 나옴' ≥ 35% | "'크게 나옴' 언급이 많습니다. '여유 있는 핏' 안내 또는 사이즈 다운 추천 문구 검토" |
| 비침 중 '있음' ≥ 30% | "비침 언급 비율이 높습니다. 이너 착용 안내·실측 촬영컷 보강 권장" |
| 예상 불만율 ≥ 카테고리 평균 ×1.5 | "유사 상품군 불만율이 카테고리 평균을 크게 웃돕니다. 입고 전 검수·QC 강화 검토" |
| 예상 불만율 ≤ 카테고리 평균 ×0.6 | "불만 신호가 적은 안정적인 조합입니다" |
| 해당 규칙 없음 | "뚜렷한 리스크 신호 없음 — 유사 상품 리뷰 발췌를 직접 확인해 보세요" |

**정직성 게이트:** 유사 상품 < 3개 또는 리뷰 합 < 15건 → 결과 블록 대신 "조건에 맞는 데이터가 부족합니다(유사 상품 N개). 속성을 줄이거나 카테고리 평균을 참고하세요" + 카테고리 평균 통계만 표시.

- [ ] **Step 1: 입력 패널 마크업/JS + 상태 관리(`state = {cat, sel, band}`) 구현, 변경 시 `render()` 호출**
- [ ] **Step 2: `findSimilar` + 결과 5블록 렌더 구현 (막대 차트는 dataviz 스킬 규칙 적용한 인라인 SVG)**
- [ ] **Step 3: 빌드 후 브라우저 스팟체크** — 언더웨어·홈웨어 + 여름 + 얇음 선택 → 사이즈 '작게 나옴' 리스크 신호와 액션 문구가 뜨는지, 속성 0개 선택 시 카테고리 전체 기준으로 동작하는지, 유사 상품 부족 조합에서 데이터 부족 안내가 뜨는지
- [ ] **Step 4: Commit** — `git commit -m "탭1: 신상품 리뷰 미리보기 (유사 상품 기반 예측)"`

---

### Task 4: 탭 2 — 브랜드 프로필

**Files:**
- Modify: `kurly/dashboard_template.html` (`#tab-brand` 마크업 + JS)

**Interfaces:**
- Consumes: `DATA.brands`, `DATA.cat_stats`, `DATA.meta.cats`

**UI 구성:**

- 브랜드 선택: 검색 가능한 드롭다운(`<select>` + 상단 요약 "상품 3개 이상 브랜드 {N}개")
- 프로필 카드: 상품 수 · 리뷰 수 · 평균 가격 / 불만율(전체 평균 대비 `▲ +N%p` 빨강 · `▼ -N%p` 초록) / 사이즈 경향(정사이즈·크게·작게 100% 스택 막대 + 전체 평균 대비 코멘트) / 주력 착용상황·계절감 상위 2개 칩 / 자주 나오는 불만 사유 상위 3개 / 소속 상품 리스트(리뷰수·불만수)
- 리뷰 수 15건 미만 브랜드는 카드 상단에 "표본이 작아 참고용" 배지

- [ ] **Step 1: 드롭다운 + 카드 렌더 구현**
- [ ] **Step 2: 빌드 후 스팟체크** — 슬로우롤리(상품 31개) 선택 시 수치가 semantic_ids CSV 합산과 일치, 표본 작은 브랜드 배지 노출
- [ ] **Step 3: Commit** — `git commit -m "탭2: 브랜드 프로필 카드"`

---

### Task 5: 탭 3 — 연구 탐색 보드

**Files:**
- Modify: `kurly/dashboard_template.html` (`#tab-explore` 마크업 + JS)

**Interfaces:**
- Consumes: `DATA.cat_stats`, `DATA.complaint_reasons`, `DATA.products[].{name,review_n,complaint_n,samples,sid}`

**UI 구성 (기존 리포트 4차트의 인터랙티브판):**

1. 속성 언급 빈도 가로 막대 — 카테고리 필터 칩(전체/165/166/169), 클릭 시 재집계
2. 카테고리별 사이즈감 100% 스택 막대 3줄 (리포트 표의 %와 일치해야 함)
3. 불만 유형 막대 (`DATA.complaint_reasons`)
4. 불만율 TOP 10 상품 테이블(리뷰 5건 이상) — 행 클릭 시 해당 상품의 `samples` 중 불만 리뷰 아코디언 펼침, SID 표기
5. 하단 파이프라인 요약 스트립: 수집(크롤러) → AI 태깅(Gemini 8축) → 코드북 정규화 → Semantic ID → 이 대시보드

- [ ] **Step 1: 차트 4개 + 파이프라인 스트립 구현**
- [ ] **Step 2: 빌드 후 수치 대조** — 사이즈감 표(패션의류 39/61/0 등)와 불만율 TOP 상품이 `output/report/insight_report_kurly.md`와 일치
- [ ] **Step 3: Commit** — `git commit -m "탭3: 연구 탐색 보드 (인터랙티브 차트)"`

---

### Task 6: 최종 검증 + README + 산출물 커밋

**Files:**
- Modify: `04_fashion_crawling/README.md` (대시보드 빌드 방법 1줄 추가)
- Commit: `kurly/output/dashboard.html`

- [ ] **Step 1: 전체 재빌드 + pytest 재실행** — `cd kurly && python build_dashboard_kurly.py && python -m pytest test_dashboard_payload.py -q` / Expected: 5 passed
- [ ] **Step 2: verify 스킬로 실동작 검증** — 브라우저(데스크톱 + 375px 모바일 뷰포트)에서 3탭 시나리오 주행, 콘솔 에러 0건, 외부 네트워크 요청 0건 확인
- [ ] **Step 3: README에 실행법 추가** (`python kurly/build_dashboard_kurly.py → kurly/output/dashboard.html`)
- [ ] **Step 4: Commit** — `git add kurly/output/dashboard.html README.md && git commit -m "컬리 리뷰 인사이트 대시보드 v1 (신상품 리뷰 미리보기·브랜드 프로필·탐색 보드)"`
- [ ] **Step 5: (사용자 확인 후) GitHub Pages 배포 안내** — 저장소 Pages 설정 또는 별도 gh-pages 사용, 링크 공유 방법을 사용자에게 안내
