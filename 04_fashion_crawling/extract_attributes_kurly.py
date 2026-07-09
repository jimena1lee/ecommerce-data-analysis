# -*- coding: utf-8 -*-
"""
컬리 리뷰 → 실착 속성 추출 스크립트 (1단계)

리뷰 텍스트를 Gemini에 배치(25건씩)로 보내서, 리뷰마다 아래 속성을
JSON으로 구조화해 추출합니다. 컬리 리뷰에는 별점이 없기 때문에
'감성/불만사유' 축을 별점 대신 사용합니다.

사용법:
    python extract_attributes_kurly.py --pilot   # 샘플 100건만 (API 4회)
    python extract_attributes_kurly.py --full    # 전체 1,548건 (API 약 62회)

중간 저장을 하므로, 도중에 끊겨도 같은 명령을 다시 실행하면
이미 처리한 리뷰는 건너뛰고 이어서 진행합니다.
"""

import argparse
import json
import os
import re
import sys
import time

import pandas as pd
from google import genai

# ── 기본 설정 ──────────────────────────────────────────────
MODEL = "gemini-3.1-flash-lite"   # 무료 티어에서 쿼터가 넉넉한 모델 (2026-07 검증)
BATCH_SIZE = 25                   # 한 번의 API 호출에 묶는 리뷰 수
WAIT_SEC = 15                     # 호출 사이 대기 시간 (분당 요청 제한 회피)
PILOT_N = 100                     # 파일럿 샘플 크기

# 카테고리 코드 → 사람이 읽을 이름 (프롬프트에 힌트로 넣어줌)
CATEGORIES = {
    "165": "패션의류(원피스·상의·하의 등)",
    "166": "신발·잡화",
    "169": "언더웨어·홈웨어",
}

DATA_DIR = "data"
OUT_PILOT = os.path.join(DATA_DIR, "kurly_attributes_pilot.csv")
OUT_FULL = os.path.join(DATA_DIR, "kurly_attributes_full.csv")

# ── Gemini에게 줄 지시문 ───────────────────────────────────
# 속성 축: 핏/사이즈감/기장/비침/두께/신축성/착용상황/계절감 + 감성/불만사유
PROMPT_HEADER = """당신은 패션 이커머스 리뷰 분석가입니다.
아래 번호가 붙은 고객 리뷰들을 읽고, 리뷰마다 실착 속성을 추출해서
JSON 배열로만 답하세요. 배열의 각 원소는 아래 키를 모두 가진 객체입니다.
리뷰에 해당 정보가 없으면 값은 null로 두세요. 추측하지 마세요.

- "id": 리뷰 번호 (정수, 입력에 표시된 번호 그대로)
- "핏": 크롭 | 오버핏 | 슬림 | 정핏 | 루즈핏 중 하나 또는 null
- "사이즈감": 정사이즈 | 크게 나옴 | 작게 나옴 중 하나 또는 null
- "기장": 짧음 | 적당 | 김 중 하나 또는 null
- "비침": 있음 | 없음 중 하나 또는 null
- "두께": 얇음 | 적당 | 두꺼움 중 하나 또는 null
- "신축성": 좋음 | 보통 | 없음 중 하나 또는 null
- "착용상황": 데일리 | 오피스 | 운동 | 홈웨어 | 외출·나들이 | 특별한 날 중 하나 또는 null
- "계절감": 여름 | 겨울 | 간절기 | 사계절 중 하나 또는 null
- "감성": 만족 | 불만 | 중립 중 하나 (반드시 채울 것)
- "불만사유": 감성이 불만이거나 리뷰에 불만 요소가 섞여 있으면
  그 이유를 짧은 명사구로 (예: "사이즈가 작음", "비침 있음", "배송 지연",
  "봉제 불량"). 없으면 null.

추가 판정 규칙:
1. "사이즈감"은 착용자가 자기 평소 사이즈 대비 크게/작게 나왔다고
   말한 경우에만 채우세요. 겉보기에 커 보인다/작아 보인다는
   디자인·비율 이야기는 사이즈감이 아니므로 null.
   (예: "귓볼이 커서 작아 보여요" → null,
        "평소 M인데 이건 작아서 L 살걸" → 작게 나옴)
2. 주얼리·가방·모자 같은 잡화는 핏/기장/비침/두께/신축성/계절감을
   원칙적으로 null로 두세요. 사이즈감은 규칙 1을 만족할 때만.
3. 신발은 사이즈감·착용상황·불만 신호에 집중하고,
   옷 전용 속성(핏/기장/비침)은 null.
4. "착용상황"과 "계절감"은 리뷰에 명시적으로 언급된 경우에만.
   상품 종류에서 추측하지 마세요. (잠옷이라고 해서 자동으로 홈웨어 아님)
5. "감성"은 리뷰 전체의 종합 톤으로 판정하되, 만족 리뷰 안에
   불만 요소가 한 줄이라도 있으면 "불만사유"에 반드시 기록하세요.
   (예: "예쁜데 세탁하니 줄었어요" → 감성: 만족, 불만사유: "세탁 후 수축")

리뷰 목록:
"""


def load_reviews() -> pd.DataFrame:
    """세 카테고리 CSV를 합쳐 하나의 DataFrame으로 만든다.
    review_id는 '카테고리코드-행번호' 형태로 만들어 이어하기에 사용."""
    frames = []
    for code in CATEGORIES:
        df = pd.read_csv(os.path.join(DATA_DIR, f"kurly_reviews_{code}_20260709.csv"))
        df["category"] = code
        df["review_id"] = [f"{code}-{i}" for i in range(len(df))]
        frames.append(df)
    all_df = pd.concat(frames, ignore_index=True)
    # 본문이 비었거나 너무 짧은 리뷰(속성 추출 불가)는 제외
    all_df = all_df[all_df["Review Body"].str.len().fillna(0) >= 10].reset_index(drop=True)
    return all_df


def build_prompt(batch: pd.DataFrame) -> str:
    """리뷰 배치를 번호 붙은 목록으로 만들어 프롬프트에 붙인다."""
    lines = []
    for n, (_, row) in enumerate(batch.iterrows(), start=1):
        cat_name = CATEGORIES[row["category"]]
        # 구매 옵션(사이즈/컬러)이 Reviewer Info에 들어 있어 힌트로 제공
        option = str(row.get("Reviewer Info", "") or "")
        body = str(row["Review Body"])[:500]  # 지나치게 긴 리뷰는 500자로 자름
        lines.append(
            f"[{n}] (카테고리: {cat_name} / 구매옵션: {option})\n"
            f"상품명: {row['Product Name']}\n리뷰: {body}\n"
        )
    return PROMPT_HEADER + "\n".join(lines)


def parse_response(text: str, batch: pd.DataFrame) -> list[dict]:
    """모델 응답(JSON 배열)을 파싱해서 review_id와 다시 연결한다."""
    # 혹시 응답이 ```json ... ``` 으로 감싸져 있으면 벗겨냄
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    items = json.loads(text)
    ids = list(batch["review_id"])
    rows = []
    for item in items:
        n = int(item.get("id", 0))
        if 1 <= n <= len(ids):
            item["review_id"] = ids[n - 1]
            item.pop("id", None)
            rows.append(item)
    return rows


def main():
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true", help="샘플 100건만 처리")
    mode.add_argument("--full", action="store_true", help="전체 리뷰 처리")
    args = ap.parse_args()

    out_path = OUT_PILOT if args.pilot else OUT_FULL

    all_df = load_reviews()
    print(f"전체 리뷰 {len(all_df)}건 로드 (카테고리별: "
          f"{all_df['category'].value_counts().to_dict()})")

    if args.pilot:
        # 카테고리 비율을 유지하면서 100건 샘플 (random_state 고정 → 재현 가능)
        target = all_df.groupby("category", group_keys=False).apply(
            lambda g: g.sample(frac=PILOT_N / len(all_df), random_state=42)
        )
        target = target.head(PILOT_N)
    else:
        target = all_df

    # ── 이어하기: 이미 처리된 review_id는 건너뜀 ──
    done_ids = set()
    if os.path.exists(out_path):
        done_ids = set(pd.read_csv(out_path)["review_id"])
        print(f"기존 결과 {len(done_ids)}건 발견 → 건너뛰고 이어서 진행")
    target = target[~target["review_id"].isin(done_ids)]

    n_batches = -(-len(target) // BATCH_SIZE)  # 올림 나눗셈
    print(f"처리할 리뷰 {len(target)}건 → API 호출 {n_batches}회 예정 "
          f"(호출당 {BATCH_SIZE}건, 호출 간 {WAIT_SEC}초 대기)")
    if n_batches == 0:
        print("처리할 리뷰가 없습니다. 완료!")
        return

    client = genai.Client()  # 환경변수 GEMINI_API_KEY 사용

    for b in range(n_batches):
        batch = target.iloc[b * BATCH_SIZE:(b + 1) * BATCH_SIZE]
        prompt = build_prompt(batch)
        print(f"[{b + 1}/{n_batches}] {len(batch)}건 요청 중...", flush=True)
        # 네트워크 일시 오류(와이파이 끊김 등)는 30초 쉬고 최대 5회 재시도
        for attempt in range(5):
            try:
                resp = client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},  # JSON 모드
                )
                rows = parse_response(resp.text, batch)
                break
            except Exception as e:
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    # 429가 나면 어떤 쿼터(분당/하루)에 걸렸는지 확인이 중요
                    print(f"  !! 쿼터 초과: {msg[:300]}")
                    print("  지금까지의 결과는 저장돼 있으니, 잠시 후 같은 명령으로 이어하세요.")
                    sys.exit(1)
                if attempt < 4 and ("Connect" in type(e).__name__ or "getaddrinfo" in msg
                                    or "timed out" in msg.lower() or "JSON" in type(e).__name__):
                    print(f"  .. 일시 오류({type(e).__name__}), 30초 후 재시도 ({attempt + 1}/5)")
                    time.sleep(30)
                    continue
                raise

        # ── 배치마다 즉시 저장 (중간에 끊겨도 결과 보존) ──
        out_df = pd.DataFrame(rows)
        # 원본 정보(상품명·카테고리·본문)도 붙여서 저장하면 검수가 편함
        meta = batch.set_index("review_id")[["category", "Product Name", "Review Body"]]
        out_df = out_df.join(meta, on="review_id")
        out_df.to_csv(out_path, mode="a", index=False, encoding="utf-8-sig",
                      header=not os.path.exists(out_path))
        print(f"  -> {len(rows)}건 추출·저장 완료 (누적 파일: {out_path})")

        if b < n_batches - 1:
            time.sleep(WAIT_SEC)  # 분당 요청 제한 회피용 대기

    print("\n완료!")


if __name__ == "__main__":
    main()
