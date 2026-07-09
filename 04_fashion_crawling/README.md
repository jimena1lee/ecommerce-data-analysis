# 04. 패션 이커머스 크롤링 (무신사 · 컬리)

무신사/컬리 카테고리별 상품 정보와 상품 리뷰를 수집하는 크롤러입니다.
수집한 데이터는 카테고리별 가격대·할인율 분포, 리뷰 텍스트 분석(불만 키워드,
사이즈 피드백), 채널 간 가격·할인 전략 비교 등 후속 분석의 원천 데이터로
사용합니다.

| 채널 | 스크립트 | 대상 |
| --- | --- | --- |
| 무신사 | `musinsa_crawler.py` | 카테고리 인기순 상품 + 리뷰 |
| 컬리 | `kurly_crawler.py` | 패션 카테고리(165, 166, 169) 상품 + 후기 |

## 수집 스키마

**상품 (products)**

```json
{
  "Channel": "무신사",
  "Category": "아우터",
  "Rank": "3",
  "Product Name": "오버핏 퀼팅 패딩 점퍼",
  "Brand": "OO",
  "Price": "89,000",
  "Original Price": "129,000",
  "Discount Rate": "31%",
  "Review Count": "1,247",
  "Rating": "4.8",
  "Collected Date": "2026-01-06"
}
```

**리뷰 (reviews)**

```json
{
  "Channel": "무신사",
  "Product Name": "오버핏 퀼팅 패딩 점퍼",
  "Rating": "5",
  "Review Body": "핏이 예쁘고 가벼워요. 다만 주머니가 좀 얕아서...",
  "Review Date": "2026-01-05",
  "Reviewer Info": "165cm / 55kg / M 구매"
}
```

## 사용법 — 무신사 (musinsa_crawler.py)

> ⚠️ 반드시 **로컬(한국 IP) 환경**에서 실행하세요. 클라우드/해외 IP는 차단될 수 있습니다.

```bash
pip install -r requirements.txt

# 1) 아우터(002) 인기순 상품 1페이지(40개) 수집
python musinsa_crawler.py products --category 002 --pages 1

# 2) 특정 상품 리뷰 50건 수집 (상품 URL: musinsa.com/products/3082392)
python musinsa_crawler.py reviews --goods-no 3082392 --max-reviews 50

# 3) 1)에서 만든 상품 목록 전체의 리뷰를 상품당 30건씩 수집
python musinsa_crawler.py reviews --from-products data/products_002_20260708.json --per-product 30
```

결과는 `data/` 폴더에 JSON과 CSV(엑셀 호환 UTF-8 BOM)로 저장됩니다.
`data/` 폴더는 git에 커밋되지 않습니다(아래 데이터 윤리 참고).

> 💡 Windows: 스크립트가 출력을 UTF-8로 강제하므로 대부분 그대로 잘 보이지만,
> 구형 cmd 콘솔에서 한글 로그가 깨지면 `chcp 65001`을 먼저 실행하세요.
> 표시만 깨질 뿐 저장되는 파일은 항상 정상 UTF-8입니다.

카테고리 코드는 무신사 카테고리 페이지 URL에서 확인합니다.
예: `https://www.musinsa.com/category/002` → 아우터 = `002`

## 사용법 — 컬리 (kurly_crawler.py)

> ⚠️ 무신사와 마찬가지로 **로컬(한국 IP) 환경**에서 실행하세요.

```bash
# 1) 패션 카테고리(165) 상품 1페이지(96개) 수집
python kurly_crawler.py products --category 165 --pages 1

# 2) 특정 상품 후기 50건 수집 (상품 URL: kurly.com/goods/1000123456)
python kurly_crawler.py reviews --product-no 1000123456 --max-reviews 50

# 3) 1)에서 만든 상품 목록 전체의 후기를 상품당 30건씩 수집
python kurly_crawler.py reviews --from-products data/kurly_products_165_20260709.json --per-product 30
```

카테고리 코드는 컬리 카테고리 페이지 URL에서 확인합니다.
예: `https://www.kurly.com/categories/165` → `165`
(현재 대상: 패션 카테고리 165 · 166 · 169.
`kurly_crawler.py`의 `CATEGORY_NAMES`에 페이지 상단 타이틀을 보고 이름을 채우세요.)

**무신사와 다른 점**

- **인증 토큰**: 컬리 API는 요청에 `Authorization: Bearer` 토큰을 요구할 수
  있습니다. 401이 나오면 ① 컬리 페이지를 연 상태로 개발자도구 Network 탭에서
  `api.kurly.com` 요청을 하나 클릭 → ② Request Headers의 `authorization` 값을
  복사 → ③ `KURLY_TOKEN` 환경변수 또는 `--token` 옵션으로 넘기세요.
  (비로그인 게스트 토큰이면 충분하며, **로그인 계정 토큰은 쓰지 마세요.**)
- **별점 없음**: 컬리 후기에는 별점 제도가 없어 `Rating` 컬럼이 항상 빈 값입니다.
- **브랜드 필드 없음**: 목록 API에 브랜드가 따로 없어 상품명 앞의
  `[브랜드]` 패턴에서 추출합니다.
- **리뷰 페이지네이션**: 페이지 번호가 아니라 커서(`after`) 방식입니다.
- **HTML 폴백**: 상품 목록 API가 404/빈 응답이면 카테고리 페이지 HTML의
  `__NEXT_DATA__`(서버렌더링 데이터)에서 상품을 자동 추출합니다. 이때
  페이지가 실제로 쓰는 API 주소 힌트를 콘솔에 출력하므로, 그 값으로
  `PRODUCTS_API`/`REVIEWS_API` 상수를 갱신하면 됩니다. 카테고리명도
  페이지 타이틀에서 자동 인식합니다.

## EDA · 대시보드

- `analysis.ipynb` — 무신사 속옷/홈웨어(026) EDA
- `analysis_kurly.ipynb` — 컬리 패션 카테고리 EDA.
  상단 `CATEGORY` 변수만 바꾸면 165·166·169 등 수집해 둔 카테고리를 전환할 수 있고,
  별점이 없는 컬리 특성에 맞춰 평점 분석 대신 리뷰수 집중도(파레토)를 본다.
- `app.py` — 수집 데이터 대시보드 (Gradio).
  `data/`의 products/reviews 파일을 채널·카테고리별로 자동 인식해
  가격 분포 · 할인 구조 · 브랜드 구도 · 리뷰 키워드를 한 화면에서 비교한다.
- `portfolio.html` — 포트폴리오용 원페이지 리포트 (정적 HTML, 차트 임베드).
  브라우저로 바로 열리며, 호스팅(GitHub Pages 등) 후 노션 `/embed`로 넣을 수 있다.
  공개 산출물 원칙에 따라 집계 통계·시각화만 포함.

```bash
pip install -r requirements.txt
python app.py   # http://127.0.0.1:7860
```

## 엔드포인트 확인 방법 (파싱이 깨졌을 때)

내부 API는 사이트 개편 시 예고 없이 바뀝니다. 응답이 비거나 필드가 어긋나면:

1. Chrome에서 해당 채널의 카테고리 페이지(또는 상품 상세의 리뷰 영역)를 엽니다.
2. 개발자도구(F12) → **Network 탭** → `Fetch/XHR` 필터를 켭니다.
3. 페이지를 스크롤하면 JSON 요청이 보입니다.
   - 무신사: `plp/goods`, `review/v1/view/list`
   - 컬리: `categories/{코드}/products`, `product-review`
4. 해당 요청의 URL·쿼리 파라미터를 각 크롤러 상단 상수에 반영합니다.
5. `--dump-raw` 옵션으로 원본 응답을 저장해 실제 키 이름을 확인하고,
   파싱부의 `first_of(...)` 후보 키를 갱신합니다.

## 데이터 수집 원칙 (중요)

- **비상업 · 학습/포트폴리오 목적**으로만 수집합니다.
- 요청 간 1.5~3초 딜레이를 유지하고, 분석에 필요한 최소량만 수집합니다.
- 수집한 **원본 데이터는 저장소나 포트폴리오에 공개하지 않습니다.**
  공개 산출물에는 집계 통계·시각화·분석 결과만 싣습니다.
  (리뷰 원문 대량 재배포는 저작권·데이터베이스권 침해 소지가 있습니다.)
- 리뷰의 키/몸무게/닉네임 등은 개인정보성 데이터이므로 공개 시 익명화합니다.
- 사이트가 차단(403/429)하면 수집을 중단합니다.

## 다음 단계 (예정)

- [x] 수집 데이터 EDA 노트북 (`analysis.ipynb` — 속옷/홈웨어 026: 가격·할인·브랜드·평점·리뷰 텍스트)
- [x] 컬리 패션 카테고리 확장 (`kurly_crawler.py` — 165 · 166 · 169)
- [x] 컬리 로컬 실행 검증: 실제 엔드포인트/응답 키 반영, 카테고리명 자동 인식
- [x] 컬리 수집 데이터 EDA 노트북 (`analysis_kurly.ipynb`)
- [x] Gradio 대시보드 (`app.py` — 채널·카테고리별 시각화)
- [ ] 컬리 166·169 수집 후 무신사와 가격대·할인율 비교 분석
- [ ] 리뷰 텍스트 분석 고도화: 형태소 분석기 적용, 카테고리 간 비교
- [ ] 29CM · W컨셉 확장 (채널 간 가격/할인 전략 비교)
