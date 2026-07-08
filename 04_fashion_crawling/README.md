# 04. 패션 이커머스 크롤링 (무신사)

무신사 카테고리별 인기 상품 정보와 상품 리뷰를 수집하는 크롤러입니다.
수집한 데이터는 카테고리별 가격대·할인율 분포, 리뷰 텍스트 분석(불만 키워드,
사이즈 피드백) 등 후속 분석의 원천 데이터로 사용합니다.

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

## 사용법

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

## 엔드포인트 확인 방법 (파싱이 깨졌을 때)

내부 API는 사이트 개편 시 예고 없이 바뀝니다. 응답이 비거나 필드가 어긋나면:

1. Chrome에서 무신사 카테고리 페이지(또는 상품 상세의 리뷰 영역)를 엽니다.
2. 개발자도구(F12) → **Network 탭** → `Fetch/XHR` 필터를 켭니다.
3. 페이지를 스크롤하면 `plp/goods`, `review/v1/view/list` 같은 JSON 요청이 보입니다.
4. 해당 요청의 URL·쿼리 파라미터를 `musinsa_crawler.py` 상단 상수에 반영합니다.
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
- [ ] 리뷰 텍스트 분석 고도화: 형태소 분석기 적용, 카테고리 간 비교
- [ ] 29CM · W컨셉 확장 (채널 간 가격/할인 전략 비교)
