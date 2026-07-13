# 포트폴리오 v2 (컬리 톤 전면 개편) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v1 미니멀 포트폴리오를 컬리 퍼플 디자인 시스템 + 스크롤 모션(고정 내비, 풀스크린 히어로, 스크롤 리베일, 블러 텍스트)으로 전면 개편하고 증거물 이미지 4장을 추가한다.

**Architecture:** `portfolio/index.html` 단일 파일 전면 재작성. CSS 인라인 `<style>`, JS 인라인 `<script>` (IntersectionObserver 리베일 ~20줄). 이미지는 `portfolio/assets/`에 영문 파일명으로 복사.

**Tech Stack:** 순수 HTML/CSS/JS, GitHub Pages

## Global Constraints

- 전화번호 절대 포함 금지 (`010-9989-7756`, `9989`, `7756` 등 어떤 형태로도)
- 연락처: `daemie@naver.com`, LinkedIn `https://www.linkedin.com/in/jiwon-lee-5760673ba/`, GitHub `https://github.com/jimena1lee`만
- 메인 컬러 `#5f0080`(컬리 퍼플), 틴트 `#f7f0fa`, 흰 바탕
- 콘텐츠 문구·순서는 v1(`portfolio/index.html` 기존 버전)과 동일 — 10개 섹션 유지
- iframe 5개 + `../04_fashion_crawling/brand-video.mp4` 영상 유지, 전부 `loading="lazy"`
- 라이브러리·외부 요청 0 (폰트 CDN 금지, 시스템 폰트 스택)
- `prefers-reduced-motion: reduce`이면 모든 모션 비활성
- 375px 뷰포트에서 페이지 가로 스크롤 없음

---

### Task 1: 증거물 이미지 복사

**Files:**
- Create: `portfolio/assets/iprime-growth.png` (원본 `C:/Users/daemi/Downloads/bn.png`)
- Create: `portfolio/assets/iprime-app-banner.png` (원본 `C:/Users/daemi/Downloads/아이프라임_thumbnail_롤링배너.png`)
- Create: `portfolio/assets/novita-brand-deal.png` (원본 `C:/Users/daemi/Downloads/노비타 브랜드딜2.png`)
- Create: `portfolio/assets/araetmok-detail.jpg` (원본 `C:/Users/daemi/Downloads/evidence_아랫목마을.jpg`)

**Interfaces:**
- Produces: 위 4개 경로 — Task 2의 `<img src="assets/...">`가 참조

- [ ] **Step 1: 복사**

```bash
mkdir -p "C:/Users/daemi/OneDrive/바탕 화면/github/ecommerce-data-analysis/portfolio/assets"
cp "C:/Users/daemi/Downloads/bn.png" ".../portfolio/assets/iprime-growth.png"
cp "C:/Users/daemi/Downloads/아이프라임_thumbnail_롤링배너.png" ".../portfolio/assets/iprime-app-banner.png"
cp "C:/Users/daemi/Downloads/노비타 브랜드딜2.png" ".../portfolio/assets/novita-brand-deal.png"
cp "C:/Users/daemi/Downloads/evidence_아랫목마을.jpg" ".../portfolio/assets/araetmok-detail.jpg"
```
(`...` = 저장소 절대 경로)

- [ ] **Step 2: 검증** — `ls portfolio/assets` → 4개 파일, 총 ~1.5MB

- [ ] **Step 3: 커밋** — `git add portfolio/assets && git commit -m "Add portfolio evidence images"`

### Task 2: index.html 전면 재작성

**Files:**
- Modify: `portfolio/index.html` (전체 교체 — 콘텐츠 문구는 기존 파일에서 그대로 가져옴)

**Interfaces:**
- Consumes: Task 1의 `assets/*.png|jpg`, 기존 iframe·영상 상대 경로

- [ ] **Step 1: 재작성**

핵심 메커니즘 코드:

디자인 토큰·리베일 CSS:
```css
:root { --kurly:#5f0080; --kurly-tint:#f7f0fa; --ink:#1c1c1e; --sub:#6e6e73;
        --line:#e8e2ec; --card-shadow:0 10px 36px rgba(95,0,128,.08); }
.reveal { opacity:0; transform:translateY(22px);
  transition:opacity .7s cubic-bezier(.28,.11,.32,1), transform .7s cubic-bezier(.28,.11,.32,1); }
.reveal.in { opacity:1; transform:none; }
.d1{transition-delay:.08s} .d2{transition-delay:.16s} .d3{transition-delay:.24s}
.bw { display:inline-block; filter:blur(10px); opacity:0;
  transition:filter .9s ease .15s, opacity .9s ease .15s; }
.in .bw, .bw.in { filter:none; opacity:1; }
@media (prefers-reduced-motion: reduce) {
  .reveal,.bw { opacity:1; transform:none; filter:none; transition:none; } }
```

고정 내비 (블러 유리):
```css
nav { position:fixed; top:0; left:0; right:0; z-index:100; height:52px;
  display:flex; align-items:center; justify-content:space-between;
  padding:0 20px; background:rgba(255,255,255,.72);
  backdrop-filter:saturate(180%) blur(18px); -webkit-backdrop-filter:saturate(180%) blur(18px);
  border-bottom:1px solid rgba(95,0,128,.08); }
nav .menu { display:flex; gap:20px; overflow-x:auto; white-space:nowrap; }
```

히어로 (퍼플 그라데이션):
```css
#hero { min-height:100svh; display:flex; flex-direction:column;
  align-items:center; justify-content:center; text-align:center;
  background:
    radial-gradient(60% 50% at 70% 20%, rgba(95,0,128,.10) 0%, transparent 70%),
    radial-gradient(50% 40% at 20% 80%, rgba(95,0,128,.07) 0%, transparent 70%),
    linear-gradient(180deg,#faf6fc 0%,#fff 100%); }
```
히어로 내용: eyebrow → `<h1>"컬리 안에서 <span class="bw">패션을 성립시키는</span> MD"</h1>`
→ 소개 문장 → 스탯 칩 3개(`.chip.reveal.d1/.d2/.d3`: 경력 8년 / ROAS 37배 / 리뷰 1,543건 분석)
→ 스크롤 화살표(bounce keyframes).

리베일 JS (body 끝):
```html
<script>
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
}), { threshold: 0.1, rootMargin: '0px 0px -60px 0px' });
document.querySelectorAll('.reveal, .bw').forEach(el => {
  if (el.getBoundingClientRect().top < innerHeight) el.classList.add('in');
  else io.observe(el);
});
</script>
```
`html { scroll-behavior:smooth; }` + 각 섹션 `scroll-margin-top:64px`.

콜아웃·카드:
```css
.card { background:#fff; border:1px solid var(--line); border-radius:16px;
        padding:24px; box-shadow:var(--card-shadow); }
.callout-problem { background:#f5f5f7; border-radius:14px; padding:18px 20px; }
.callout-result  { background:var(--kurly-tint); border-radius:14px; padding:18px 20px; }
.callout-result .num { color:var(--kurly); font-weight:800; }
```

증거물 이미지:
```html
<figure class="evidence reveal">
  <img src="assets/iprime-growth.png" alt="아이프라임 성장 인포그래픽" loading="lazy">
  <figcaption>📎 증거물 — …</figcaption>
</figure>
```
프로젝트 03은 `.evidence-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }`
(모바일 `1fr`)에 2장, 04·05는 단독 1장(`max-width:520px` 중앙).

섹션 순서·문구: 기존 v1 index.html의 10개 섹션 그대로. 섹션 제목은
eyebrow(퍼플 소문자 라벨) + h2 구조로. 적합성 강점 3개는 카드 3장 세로 배치.
경험 표는 thead 배경 `var(--kurly-tint)`. 마무리 문장의 "컬리는 고객의 냉장고를
압니다" 구간에 `.bw` 적용. 내비 앵커: `#fit 적합성 / #mining 리뷰 분석 /
#exp 경험 / #projects 프로젝트 / #ai AI 역량`.

- [ ] **Step 2: 전화번호 검증** — `grep -E "9989|7756|010-" portfolio/index.html` → 매칭 0

- [ ] **Step 3: 로컬 미리보기 검증** — repo-root 서버(포트 8377)에서 `/portfolio/` 열기.
  확인: 내비 고정+블러, 히어로 100svh+칩 시차 등장, 스크롤 리베일 동작,
  iframe 5개·이미지 4장·영상 로드, 콘솔 에러 0, 375px 가로 스크롤 없음.

- [ ] **Step 4: 커밋** — `git add portfolio/index.html && git commit -m "Redesign portfolio with Kurly-toned design and scroll motion"`

### Task 3: 배포 및 확인

**Files:** 없음 (푸시만)

**Interfaces:**
- Consumes: Task 1·2 커밋
- Produces: `https://jimena1lee.github.io/ecommerce-data-analysis/portfolio/` 갱신

- [ ] **Step 1: 푸시** — `git push origin main`
- [ ] **Step 2: 실주소 확인** — 반영 대기 후 curl 200 + WebFetch로 히어로 문구·섹션 확인
