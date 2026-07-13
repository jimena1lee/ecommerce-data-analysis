# 포트폴리오 페이지 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 노션 포트폴리오(컬리 패션 MD 지원용)를 `portfolio/index.html` 단일 정적 HTML 페이지로 재구축해 GitHub Pages에 배포한다.

**Architecture:** 빌드 도구 없는 단일 HTML 파일. CSS는 `<style>` 인라인, JS 없음(영상은 네이티브 `<video>`). 결과물 5개는 iframe으로 삽입하고 상대 경로를 사용해 로컬 미리보기에서도 동작.

**Tech Stack:** 순수 HTML/CSS, GitHub Pages (main 브랜치 루트 서빙)

## Global Constraints

- 전화번호(`010-9989-7756` 등 어떤 형태로도) 절대 포함 금지 — 공개 웹 노출 방지
- 연락처는 이메일 `daemie@naver.com`, LinkedIn `https://www.linkedin.com/in/jiwon-lee-5760673ba/`, GitHub `https://github.com/jimena1lee`만
- 디자인: 흰 배경, 검정/회색 타이포 중심 미니멀, 브랜드 컬러 없음, 성과 숫자만 굵게 강조
- 반응형: 375px 뷰포트에서 페이지 가로 스크롤 없음 (표는 자체 가로 스크롤 컨테이너)
- 노션 S3 링크(만료됨) 사용 금지 — 영상은 저장소 내 `04_fashion_crawling/brand-video.mp4`
- 콘텐츠 원문은 스펙(`docs/superpowers/specs/2026-07-13-portfolio-page-design.md`)의 페이지 구성 순서를 따르고, 문구는 노션 원본 텍스트를 그대로 사용

---

### Task 1: portfolio/index.html 작성

**Files:**
- Create: `portfolio/index.html`

**Interfaces:**
- Consumes: 저장소 내 기존 산출물 (아래 상대 경로)
  - `../04_fashion_crawling/kurly/output/dashboard.html`
  - `../04_fashion_crawling/output/portfolio.html`
  - `../04_fashion_crawling/instagram-feed-v5.html`
  - `../04_fashion_crawling/runningshoes-gpt.html`
  - `../04_fashion_crawling/brand-video.mp4`
  - 외부: `https://jimena1lee.github.io/miniproject-recommendation-runningshoe/mockup.html`
- Produces: 완성된 정적 페이지 (다른 태스크가 의존하는 코드 인터페이스 없음)

- [ ] **Step 1: HTML 파일 작성**

문서 뼈대와 스타일 규칙:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>이지원 — 이커머스 MD·마케터 포트폴리오</title>
<style>
  :root { --ink:#111; --sub:#666; --line:#e5e5e5; --bg:#fff; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font-family:'Apple SD Gothic Neo','Pretendard','Noto Sans KR',sans-serif;
         line-height:1.7; -webkit-font-smoothing:antialiased; }
  main { max-width:760px; margin:0 auto; padding:64px 20px 96px; }
  h1 { font-size:2rem; margin:0 0 4px; letter-spacing:-.02em; }
  h2 { font-size:1.25rem; margin:72px 0 8px; padding-bottom:12px;
       border-bottom:1px solid var(--ink); letter-spacing:-.01em; }
  h3 { font-size:1.05rem; margin:40px 0 4px; }
  .sub { color:var(--sub); }
  .meta { color:var(--sub); font-size:.9rem; }
  a { color:inherit; }
  strong { font-weight:700; }
  .num { font-weight:700; }               /* 성과 숫자 강조 */
  .quote { border-left:2px solid var(--ink); padding-left:16px;
           color:var(--sub); margin:24px 0; }
  .tablewrap { overflow-x:auto; }          /* 표 가로 스크롤 */
  table { border-collapse:collapse; width:100%; min-width:560px; font-size:.92rem; }
  th,td { border-top:1px solid var(--line); padding:10px 12px; text-align:left;
          vertical-align:top; }
  th { font-weight:700; white-space:nowrap; }
  .embed { margin:24px 0; }
  .embed iframe { width:100%; border:1px solid var(--line); border-radius:8px; }
  .embed .open { display:block; text-align:right; font-size:.85rem;
                 color:var(--sub); margin-top:6px; }
  video { width:100%; max-width:480px; display:block; margin:24px auto;
          border-radius:8px; }
  @media (max-width:600px){ main{padding:40px 16px 64px;} h1{font-size:1.6rem;} }
</style>
</head>
<body>
<main>
  <!-- 이하 섹션 -->
</main>
</body>
</html>
```

iframe 삽입 패턴 (5개 결과물 모두 동일 패턴, 높이만 조정):

```html
<div class="embed">
  <iframe src="../04_fashion_crawling/kurly/output/dashboard.html"
          height="620" loading="lazy" title="신규 입점 상품·브랜드 평가 대시보드"></iframe>
  <a class="open" href="../04_fashion_crawling/kurly/output/dashboard.html"
     target="_blank" rel="noopener">새 창에서 크게 보기 ↗</a>
</div>
```

브랜드 영상:

```html
<video src="../04_fashion_crawling/brand-video.mp4"
       autoplay muted loop playsinline controls preload="metadata"></video>
```

섹션 순서와 콘텐츠 (문구는 노션 원본 그대로, 스펙 '페이지 구성' 참조):

1. 헤더: `이지원` / `이커머스 MD·마케터 (만 8년) · 지원 포지션: 패션 MD · 컬리(Kurly)` / 이메일·LinkedIn·GitHub 링크 (전화번호 없음)
2. 소개: "컬리 안에서 패션을 성립시키는 MD"입니다. + 장보기 고객 전환 문단
3. 한눈에 보는 적합성: 강점 3개(이커머스 세일즈 구조 이해 / 페르소나 기반 큐레이션 / 데이터 의사결정) 각각 하위 근거 리스트 포함
4. 컬리패션 리뷰 1,543건 마이닝: 요약 3포인트(언더웨어·홈웨어 55%, 식품→패션 전환 리뷰 인용, 홈웨어→원마일웨어→애슬레저 로드맵) + ① 대시보드 iframe + ② 경쟁사 비교 iframe
5. 나의 경험: 2열 표 7행 (컬리 패션 MD 요건 / 나의 경험·근거) — 노션 표 내용 그대로
6. 대표 프로젝트 01~05: 각 프로젝트 = 제목 + 직함·기간(meta) + 문제 + 핵심 액션 리스트 + 성과 + 인용문. 01에 인스타 피드 iframe 포함. 성과 수치(YoY 185%▲, ROAS 약 37배, 월평균 1.2억 등)는 `<span class="num">`으로 강조
7. 데이터·툴 역량: 4줄 리스트 (데이터·분석 / 커머스 운영 / 마케팅 / AI)
8. AI 역량 증거 ① 러닝화 추천 챗봇: 설명 문단 + iframe 2개 (runningshoes-gpt.html 상대 경로, mockup.html 외부 절대 URL)
9. AI 역량 증거 ② 광고 콘텐츠: 설명 문단 + 브랜드 영상 video 태그
10. 마무리 "왜 컬리 패션 MD인가": "무신사는 고객의 옷장을 알지만, 컬리는 고객의 냉장고를 압니다..." 문단

- [ ] **Step 2: 전화번호 미포함 검증**

Run: `grep -c "9989" portfolio/index.html` → 기대: `0` (매칭 없음, exit 1)

- [ ] **Step 3: 로컬 미리보기 검증**

로컬 서버로 저장소 루트를 서빙해 `portfolio/` 열기.
확인 항목: 전체 레이아웃 렌더링, iframe 5개 로드, 표 렌더링, 영상 재생,
375px 뷰포트에서 페이지 가로 스크롤 없음.

- [ ] **Step 4: 커밋**

```bash
git add portfolio/index.html
git commit -m "Add minimal portfolio page for GitHub Pages"
```

### Task 2: 배포 및 실서비스 확인

**Files:**
- Modify: 없음 (푸시만)

**Interfaces:**
- Consumes: Task 1의 커밋
- Produces: 공개 URL `https://jimena1lee.github.io/ecommerce-data-analysis/portfolio/`

- [ ] **Step 1: 푸시**

```bash
git push origin main
```

- [ ] **Step 2: 배포 확인**

1~2분 대기 후 `https://jimena1lee.github.io/ecommerce-data-analysis/portfolio/` 접속.
확인 항목: 페이지 로드, iframe 5개 동작, 영상 재생.
(외부 miniproject 저장소 목업이 안 뜨면 해당 저장소 Pages 설정 확인 — 이번 범위 밖이므로 사용자에게 보고만)
