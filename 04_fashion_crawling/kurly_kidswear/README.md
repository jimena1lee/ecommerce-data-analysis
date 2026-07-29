# 컬리 키즈웨어 카탈로그 진단

카테고리 172(키즈웨어) · 919017(유아동패션) 전 상품 3,640 SKU 를 수집해
"무엇이 팔리는 조합인가"를 분석했다. 결과는
[포트폴리오 ③](https://jimena1lee.github.io/ecommerce-data-analysis/portfolio/) 에
임베드돼 있다.

스냅샷: 2026-07-28 16:10 · 3,640 SKU · 47 브랜드 · 리뷰 2,498건

## 2단 파이프라인

**1단계 — 원본 데이터 필요 (저장소에 없음)**

원본 CSV(3,640행) · raw JSON(39개) · 보정 jsonl 은 용량과 공개 범위 때문에
커밋하지 않는다. `.gitignore` 참고.

```bash
python collect_kurly.py                  # 목록 API 수집 → kurly_kidswear_<ts>.csv
python enrich_reviews.py                 # 상세 API 리뷰수 재확인 → review_counts_<ts>.jsonl
python analyze_kurly.py                  # A~F 분석 → 분석리포트_<ts>.md
python make_aggregates.py --src <원본폴더>  # → data/*.csv 9개
```

**2단계 — 저장소만으로 실행 가능**

```bash
python build_kidswear_dashboard.py       # data/ → output/kidswear_diagnosis.html
python -m pytest -q                      # 집계값·payload 검증
```

## 리뷰수 보정

목록 API 의 `review_count` 는 리뷰가 적은 상품을 0 으로 반환한다.
목록에서 0 이던 3,596건을 상세 API 로 재확인해 555건을 보정했고,
총 리뷰수가 **1,420 → 2,498**건이 됐다.

`data/` 의 모든 값은 보정 후 기준이다. 원본 CSV 를 그대로 집계하면
리포트와 어긋나므로 주의한다.

## 데이터 한계

- 리뷰수는 판매량의 대리지표다. 노출기간을 보정하지 않아 신상품에 불리하다.
- 평점은 컬리 API 가 제공하지 않아 전 행 비어 있다. 분석에 쓰지 않았다.
- 브랜드명은 상품명의 `[브랜드]` 접두사에서 추출했다(커버리지 100%, 표본 20건 검증).
- 172 와 919017 은 브랜드·상품 교집합이 0이다. 별개 매장으로 취급한다.
