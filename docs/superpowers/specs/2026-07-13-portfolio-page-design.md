# 포트폴리오 웹페이지 설계 (컬리 패션 MD 지원용)

날짜: 2026-07-13
상태: 설계 확정 (사용자 승인)

## 목표

노션 포트폴리오 페이지(🛍️ 포트폴리오 | 이지원)를 GitHub Pages에서 서빙되는
정적 HTML 페이지로 재구축한다. 노션을 그대로 복사하는 것이 아니라
웹 포트폴리오로 다시 빌드한다.

## 결정 사항

| 항목 | 결정 |
|------|------|
| 배포 위치 | 현재 저장소(`ecommerce-data-analysis`) 루트의 `portfolio/index.html` |
| 최종 주소 | `https://jimena1lee.github.io/ecommerce-data-analysis/portfolio/` |
| 구현 방식 | 빌드 도구 없는 단일 정적 HTML 파일 (HTML + CSS 인라인, 최소한의 JS) |
| 디자인 | 미니멀 포트폴리오 — 흰 배경, 타이포그래피 중심, 검정/회색 톤, 얇은 구분선. 성과 숫자는 굵게 강조. 반응형(모바일 대응) |
| 결과물 표시 | iframe으로 페이지 안에 바로 삽입 + 각 결과물마다 "새 창에서 크게 보기" 링크 |
| 연락처 | 이메일·LinkedIn·GitHub만 공개. **전화번호 제외** (공개 웹 노출 방지) |
| 브랜드 영상 | 저장소 내 `04_fashion_crawling/brand-video.mp4`(9.9MB)를 `<video muted loop playsinline autoplay preload="metadata">`로 삽입. 만료되는 노션 S3 링크는 사용하지 않음 |

## 페이지 구성 (노션 원본 순서 유지)

1. **헤더** — 이름 "이지원", 타이틀 "이커머스 MD·마케터 (만 8년)", 이메일(daemie@naver.com)·LinkedIn·GitHub 링크
2. **소개** — "컬리 안에서 패션을 성립시키는 MD" 요약 문단
3. **한눈에 보는 적합성** — 강점 3개 (세일즈 구조 이해 / 페르소나 큐레이션 / 데이터 의사결정)
4. **리뷰 1,543건 마이닝** — 분석 요약 3포인트 + iframe 2개:
   - 신규 입점 상품·브랜드 평가 대시보드: `../04_fashion_crawling/kurly/output/dashboard.html`
   - 경쟁사 비교 분석: `../04_fashion_crawling/output/portfolio.html`
5. **나의 경험** — 컬리 요건 대비 경험 2열 표 (7행)
6. **대표 프로젝트 01~05** — 각각 문제 → 핵심 액션 → 성과 구조:
   - 01 워너비즈핏 (인스타 피드 iframe: `../04_fashion_crawling/instagram-feed-v5.html`)
   - 02 인터파크 단독 상품
   - 03 아이프라임 입점 영업·온보딩
   - 04 카테고리 운영·성과 관리
   - 05 위메프 브랜드 기획·컬리 기획전
7. **데이터·툴 역량** — 4개 카테고리 리스트 (데이터·분석 / 커머스 운영 / 마케팅 / AI)
8. **AI 역량 증거 ①** — 러닝화 추천 챗봇 iframe 2개:
   - `../04_fashion_crawling/runningshoes-gpt.html`
   - `https://jimena1lee.github.io/miniproject-recommendation-runningshoe/mockup.html` (외부 저장소)
9. **AI 역량 증거 ②** — 브랜드 영상 (`brand-video.mp4`)
10. **마무리** — "왜 컬리 패션 MD인가" 문단

iframe 경로는 같은 저장소 내 상대 경로를 사용해 로컬 미리보기에서도 동작하게 한다
(외부 저장소인 러닝화 목업 1개만 절대 URL).

## 에러 처리 / 엣지 케이스

- iframe 로드 실패 대비: 각 iframe 아래 "새 창에서 크게 보기" 링크가 항상 존재
- 모바일: iframe 높이를 고정하되 내부 스크롤 허용, 표는 가로 스크롤 컨테이너로 감싸기
- 영상 자동재생이 차단된 브라우저 대비: controls 속성 포함

## 검증 방법

1. 로컬 미리보기 서버로 페이지 렌더링 확인 (레이아웃, iframe, 영상, 표)
2. 모바일 뷰포트(375px)에서 가로 스크롤 없는지 확인
3. 전화번호 문자열이 파일에 없는지 확인
4. 커밋·푸시 후 실제 GitHub Pages 주소에서 최종 확인

## 향후 (이번 범위 아님)

- 다른 회사 지원 시 내용만 교체한 변형 페이지 제작
