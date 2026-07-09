# -*- coding: utf-8 -*-
"""
리뷰 실착 속성 추출 스크립트 (1단계)

무신사 속옷/홈웨어 리뷰에서 Gemini API로 실착 속성을 구조화 추출합니다.
- 기본 실행: 파일럿 모드 (100개 샘플만 추출)
- 전체 실행: python extract_attributes.py --full

동작 순서:
  1. CSV 로드 → 중복 제거
  2. 샘플링 (파일럿: 저평점 리뷰 전부 + 나머지 상품별 층화 샘플)
  3. 리뷰 10개씩 묶어서(batch) Gemini에 요청 → JSON 응답 파싱
  4. 결과를 data/attributes_*.csv 로 저장

무료 티어 안전장치:
  - 요청 사이 6초 대기 (분당 10회 제한 안전권)
  - 429(rate limit) 에러 시 30초 대기 후 재시도 (최대 3회)
  - 배치 단위로 중간 저장 → 중단돼도 이미 처리한 결과는 남음
"""

import argparse
import io
import json
import os
import sys
import time

import pandas as pd
from google import genai

# Windows 콘솔에서 한글 출력이 깨지지 않게 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ── 설정값 ──────────────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "reviews_026_20260708.csv")
OUT_DIR = os.path.join(os.path.dirname(__file__), "data")
# 주의: 무료 티어는 "모델별 하루 요청 수" 제한이 있음 (2.5-flash/flash-lite 각 하루 20회).
# 두 모델 모두 당일 쿼터 소진 → 쿼터가 별도인 최신 flash-lite로 전환.
MODEL = "gemini-3.1-flash-lite"
BATCH_SIZE = 25              # 한 번의 API 호출에 묶을 리뷰 수
WAIT_SECONDS = 10            # 요청 간 대기 시간
PILOT_SIZE = 100             # 파일럿 샘플 수

# ── 속성 추출 프롬프트 ──────────────────────────────────
# 리뷰마다 아래 속성 축을 추출. 언급이 없으면 반드시 null.
# (없는 걸 지어내면 코드북이 오염되므로 프롬프트에서 강하게 지시)
PROMPT_HEADER = """당신은 패션 이커머스 리뷰 분석가입니다.
아래는 속옷/홈웨어 카테고리 상품 리뷰 목록입니다.
각 리뷰에서 "실제 착용 경험"에 대한 속성만 추출해 JSON 배열로 답하세요.

각 리뷰마다 다음 필드를 추출합니다:
- id: 리뷰 번호 (입력에 표시된 번호 그대로)
- 핏: 몸에 감기는 "형태"에 대한 언급만 (예: "슬림", "몸에 딱 맞음", "들뜸 없음", "넉넉함").
  편함/불편함 같은 착용감 표현은 여기 넣지 말고 "착용감"에 넣으세요.
- 착용감: 편안함/불편함에 대한 언급 (예: "편함", "불편함", "압박감 없음", "갑갑함")
- 사이즈감: 반드시 "정사이즈" / "크게 나옴" / "작게 나옴" 셋 중 하나의 단일 값 (언급 없으면 null)
- 기장: 길이에 대한 언급 (예: "짧음", "김", "적당함")
- 비침: 비침 여부 언급 (예: "비침 없음", "약간 비침")
- 두께: 두께감 언급 (예: "얇음", "도톰함", "적당함")
- 신축성: 신축성 언급 (예: "좋음", "없음", "적당함")
- 촉감: 촉감/소재감 언급 (예: "부드러움", "까슬함", "시원함")
- 착용상황: 언급된 착용 상황 목록 (예: ["운동", "수면", "데일리"], 없으면 [])
- 계절감: 계절 관련 언급 (예: "여름용", "사계절", "여름에 더움")
- 불만점: 불만/아쉬운 점이 있으면 한 문장으로 요약 (없으면 null).
  실착 관련이 아니어도 포함하세요: 색상이 화면과 다름, 검수/오염 불량, 냄새, 마감 등.
  단, 배송 속도에 대한 불만은 제외.

규칙:
1. 리뷰에 명시적으로 언급된 내용만 추출하세요. 추측 금지.
2. 언급이 없는 필드는 반드시 null (착용상황은 빈 배열 []).
3. 착용상황을 제외한 모든 필드는 단일 문자열입니다. 배열이나 쉼표로 나열하지 말고,
   언급이 여러 개면 가장 핵심적인 것 하나만 고르세요 (불만점은 한 문장으로 병합 가능).
4. 반드시 입력 리뷰 개수와 같은 길이의 JSON 배열만 출력하세요.

리뷰 목록:
"""


# LLM 응답에서 받아들일 키 목록 (이외의 키는 오타/환각이므로 버림)
EXPECTED_FIELDS = ["id", "핏", "착용감", "사이즈감", "기장", "비침", "두께",
                   "신축성", "촉감", "착용상황", "계절감", "불만점"]


def normalize_record(rec: dict) -> dict:
    """LLM이 돌려준 리뷰 1건의 결과를 검증합니다.
    - 예상 키만 남기고 나머지는 버림 (예: '불만점'을 '불man점'으로 오타 내는 경우)
    - 빠진 키는 null로 채움"""
    return {k: rec.get(k) for k in EXPECTED_FIELDS}


def load_and_dedupe(path: str) -> pd.DataFrame:
    """CSV를 읽고 상품명+리뷰본문 기준 중복을 제거합니다."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    before = len(df)
    df = df.drop_duplicates(subset=["Product Name", "Review Body"]).reset_index(drop=True)
    print(f"로드: {before}건 → 중복 제거 후 {len(df)}건")
    # 리뷰마다 고유 번호를 부여 (추출 결과와 원본을 다시 연결하는 열쇠)
    df["review_id"] = df.index
    return df


def make_pilot_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """파일럿용 샘플 추출: 저평점(1~3점)은 전부 포함 + 나머지는 상품별 층화 샘플."""
    low = df[df["Rating"] <= 3]                      # 저평점: 불만 신호 분석용이라 전부 포함
    rest = df[df["Rating"] >= 4]
    remain = n - len(low)
    # 상품별로 골고루 뽑기: 상품 순서를 섞은 뒤 각 상품에서 돌아가며 1개씩 추출
    sampled = (
        rest.sample(frac=1, random_state=42)          # 셔플
        .groupby("Product Name", group_keys=False)
        .apply(lambda g: g.reset_index(drop=True))
        .reset_index(drop=True)
    )
    # 상품별 순번을 매긴 뒤 순번이 낮은 것부터 뽑으면 모든 상품이 고르게 포함됨
    sampled["rank_in_product"] = sampled.groupby("Product Name").cumcount()
    picked = sampled.sort_values(["rank_in_product", "Product Name"]).head(remain)
    out = pd.concat([low, picked]).drop(columns=["rank_in_product"], errors="ignore")
    out = out.sort_values("review_id").reset_index(drop=True)
    print(f"파일럿 샘플: {len(out)}건 (저평점 {len(low)}건 전부 포함, 상품 {out['Product Name'].nunique()}개 커버)")
    return out


def build_batch_prompt(batch: pd.DataFrame) -> str:
    """리뷰 배치를 프롬프트 텍스트로 변환합니다."""
    lines = []
    for _, row in batch.iterrows():
        # 리뷰가 아주 길면 앞 500자만 사용 (속성은 대부분 앞부분에 언급됨 + 토큰 절약)
        body = str(row["Review Body"])[:500].replace("\n", " ")
        lines.append(f'[{row["review_id"]}] (평점 {row["Rating"]}점) {body}')
    return PROMPT_HEADER + "\n".join(lines)


def call_gemini(client: genai.Client, prompt: str, retries: int = 8) -> list:
    """Gemini 호출 → JSON 파싱. 429 에러 시 대기 후 재시도."""
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={"response_mime_type": "application/json"},  # JSON만 출력하도록 강제
            )
            # 키 검증: 오타 키 제거 + 빠진 키 null 채움
            return [normalize_record(r) for r in json.loads(resp.text)]
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                print(f"  ⚠ rate limit — 60초 대기 후 재시도 ({attempt + 1}/{retries})")
                time.sleep(60)
            elif "503" in msg or "UNAVAILABLE" in msg or "500" in msg:
                # 서버 과부하/일시 장애: 대기 시간을 점점 늘려가며 재시도 (30초, 60초, 90초...)
                wait = 30 * (attempt + 1)
                print(f"  ⚠ 서버 일시 장애(503) — {wait}초 대기 후 재시도 ({attempt + 1}/{retries})")
                time.sleep(wait)
            elif isinstance(e, json.JSONDecodeError):
                print(f"  ⚠ JSON 파싱 실패 — 재시도 ({attempt + 1}/{retries})")
                time.sleep(WAIT_SECONDS)
            else:
                raise
    raise RuntimeError("재시도 횟수 초과")


def extract(df: pd.DataFrame, out_path: str) -> pd.DataFrame:
    """배치 단위로 속성을 추출하고 중간 저장하며 진행합니다.
    out_path에 이전 실행의 중간 결과가 있으면 이어서(resume) 진행합니다."""
    client = genai.Client()  # GEMINI_API_KEY 환경변수를 자동으로 읽음
    df_all = df  # 마지막 병합에 쓸 전체 원본 (이어하기 필터링과 무관하게 보존)

    # ── 이어하기: 이전 중간 저장 파일이 있으면 처리된 리뷰는 건너뜀 ──
    results = []
    if os.path.exists(out_path):
        prev = pd.read_csv(out_path, encoding="utf-8-sig")
        if "id" in prev.columns:  # 중간 저장 형식(원시 결과)일 때만 이어하기
            results = [normalize_record(r) for r in prev.to_dict("records")]
            done_ids = {r["id"] for r in results}
            df = df[~df["review_id"].isin(done_ids)]
            print(f"이어하기: 이미 처리된 {len(done_ids)}건 건너뜀 → 남은 {len(df)}건")

    batches = [df.iloc[i : i + BATCH_SIZE] for i in range(0, len(df), BATCH_SIZE)]
    print(f"남은 {len(df)}건 → {len(batches)}회 API 호출 예정 (배치당 {BATCH_SIZE}건, 요청 간 {WAIT_SECONDS}초 대기)")

    for i, batch in enumerate(batches):
        print(f"배치 {i + 1}/{len(batches)} 처리 중...")
        parsed = call_gemini(client, build_batch_prompt(batch))
        results.extend(parsed)
        # 중간 저장: 중단되더라도 여기까지의 결과는 파일로 남음
        pd.DataFrame(results).to_csv(out_path, index=False, encoding="utf-8-sig")
        if i < len(batches) - 1:
            time.sleep(WAIT_SECONDS)

    attrs = pd.DataFrame(results)
    # 추출 결과(id)와 원본 리뷰(review_id)를 연결해 하나의 표로 합침
    attrs = attrs.rename(columns={"id": "review_id"})
    merged = df_all.merge(attrs, on="review_id", how="left")
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {out_path}")
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="전체 리뷰 실행 (기본은 100건 파일럿)")
    args = parser.parse_args()

    df = load_and_dedupe(DATA_PATH)

    if args.full:
        target, out_name = df, "attributes_full.csv"
    else:
        target, out_name = make_pilot_sample(df, PILOT_SIZE), "attributes_pilot.csv"

    extract(target, os.path.join(OUT_DIR, out_name))
