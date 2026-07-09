# -*- coding: utf-8 -*-
"""
속성 코드북 구축 스크립트 (2단계)

1단계에서 추출한 자유 표현 속성값(예: "편함", "편안함", "매우 편함")을
축별로 정규화해 카테고리 속성 코드북(JSON)을 만듭니다.

동작 순서:
  1. attributes_full.csv 로드
  2. 축별 고유 값 목록 수집
  3. Gemini 1회 호출로 "원시값 → 대표 레이블" 매핑 생성 (동의어 통합)
  4. 코드북 JSON 저장: {"핏": {"1": "밀착", "2": "넉넉", ...}, ...}
  5. 리뷰별로 코드가 부여된 attributes_coded.csv 저장

실행: python build_codebook.py
"""

import io
import json
import os
import sys
from collections import Counter

import pandas as pd
from google import genai

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.path.dirname(__file__)
IN_PATH = os.path.join(BASE, "data", "attributes_full.csv")
CODEBOOK_PATH = os.path.join(BASE, "data", "codebook_026.json")
MAPPING_PATH = os.path.join(BASE, "data", "codebook_mapping_026.json")
OUT_PATH = os.path.join(BASE, "data", "attributes_coded.csv")
MODEL = "gemini-3.1-flash-lite"  # 2.5 계열은 하루 20회 쿼터 소진으로 전환

# 코드북을 만들 속성 축 (착용상황은 리스트형이라 별도 처리)
AXES = ["핏", "착용감", "사이즈감", "기장", "비침", "두께", "신축성", "촉감", "계절감"]

# 사이즈감은 3개 표준값으로 고정 (LLM 정규화 없이 고정 코드북 사용)
FIXED = {"사이즈감": ["정사이즈", "크게 나옴", "작게 나옴"]}

# LLM이 지시를 벗어나 만든 사이즈감 변형 표현 → 표준값 수동 매핑
SIZE_CLEANUP = {
    "넉넉함": "크게 나옴", "적당함": "정사이즈", "작음": "작게 나옴",
    "작나?": "작게 나옴", "적당하고": "정사이즈", "적당하게 맞음": "정사이즈",
    "딱맞음": "정사이즈", "타이트함": "작게 나옴", "정사이즈, 크게 나옴": "정사이즈",
}

# LLM 정규화 결과 검수 후 수동 교정 (반대 의미가 한 레이블로 묶인 경우 등)
# 형식: {축: {원시값: 올바른 레이블}}
MANUAL_OVERRIDES = {
    "비침": {"비침 없음": "비침 없음", "비침": "비침 있음", "약간 티남": "비침 있음"},
    "기장": {"짧음": "짧음", "김": "김", "넉넉함": "김", "적당함": "적당함"},
}

PROMPT = """당신은 패션 이커머스 속성 사전(코드북)을 만드는 분석가입니다.
아래는 속옷/홈웨어 리뷰에서 추출한 속성 축별 원시 값 목록입니다 (값 옆 숫자는 등장 횟수).
각 축마다 의미가 같은 값들을 묶어 3~7개의 대표 레이블로 정규화하세요.

규칙:
1. 대표 레이블은 짧은 한국어 명사구 (예: "부드러움", "시원함", "밀착핏").
2. 모든 원시 값이 정확히 하나의 대표 레이블에 매핑되어야 합니다.
3. 긍정/부정 방향이 다른 값을 같은 레이블로 묶지 마세요 (예: "편함"과 "불편함"은 분리).
4. 등장 횟수가 많은 값을 중심으로 레이블 이름을 정하세요.
5. 어디에도 묶기 어려운 희소 값은 "기타" 레이블로 보내세요.

출력은 JSON 하나만:
{"축이름": {"대표레이블": ["원시값1", "원시값2", ...], ...}, ...}

원시 값 목록:
"""


def collect_values(df: pd.DataFrame) -> dict:
    """축별로 (값, 등장횟수) 목록을 수집합니다."""
    values = {}
    for axis in AXES:
        if axis in FIXED:  # 고정 코드북 축은 LLM 정규화 대상에서 제외
            continue
        counts = Counter(df[axis].dropna().astype(str).str.strip())
        if counts:
            values[axis] = counts
    return values


def build_mapping(values: dict) -> dict:
    """Gemini 1회 호출로 원시값 → 대표 레이블 매핑을 만듭니다."""
    lines = []
    for axis, counts in values.items():
        lines.append(f"\n[{axis}]")
        for val, n in counts.most_common():
            lines.append(f"- {val} ({n}회)")
    client = genai.Client()
    resp = client.models.generate_content(
        model=MODEL,
        contents=PROMPT + "\n".join(lines),
        config={"response_mime_type": "application/json"},
    )
    grouped = json.loads(resp.text)  # {축: {대표레이블: [원시값,...]}}

    # 뒤집어서 {축: {원시값: 대표레이블}} 형태로 변환 (코드 부여에 쓰기 쉬움)
    mapping = {}
    for axis, groups in grouped.items():
        mapping[axis] = {}
        for label, raws in groups.items():
            for raw in raws:
                mapping[axis][raw] = label
    return mapping


def build_codebook(df: pd.DataFrame, mapping: dict) -> dict:
    """대표 레이블에 번호를 붙여 코드북을 만듭니다. 번호는 등장 빈도 순."""
    codebook = {}
    for axis in AXES:
        if axis in FIXED:
            labels = FIXED[axis]
        else:
            # 원시값을 대표 레이블로 치환한 뒤 빈도 집계 → 빈도 높은 순으로 코드 부여
            m = mapping.get(axis, {})
            mapped = df[axis].dropna().astype(str).str.strip().map(m)
            counts = mapped.value_counts()
            labels = [l for l in counts.index if l != "기타"] + (["기타"] if "기타" in counts.index else [])
        codebook[axis] = {str(i + 1): label for i, label in enumerate(labels)}
    return codebook


def apply_codes(df: pd.DataFrame, mapping: dict, codebook: dict) -> pd.DataFrame:
    """리뷰별로 각 축의 코드 번호를 부여한 컬럼(축이름_code)을 추가합니다."""
    out = df.copy()
    for axis in AXES:
        label_to_code = {label: code for code, label in codebook[axis].items()}
        m = mapping.get(axis, {})

        def to_code(v):
            if pd.isna(v):
                return None
            raw = str(v).strip()
            label = m.get(raw, raw)  # 고정 축(사이즈감)은 원시값이 곧 레이블
            return label_to_code.get(label)

        out[f"{axis}_label"] = out[axis].map(lambda v: m.get(str(v).strip(), str(v).strip()) if pd.notna(v) else None)
        out[f"{axis}_code"] = out[axis].map(to_code)
    return out


if __name__ == "__main__":
    df = pd.read_csv(IN_PATH, encoding="utf-8-sig")
    # 사이즈감 변형 표현을 표준 3개 값으로 정리
    df["사이즈감"] = df["사이즈감"].replace(SIZE_CLEANUP)
    print(f"로드: {len(df)}건")

    # 매핑 캐시: 이미 만들어둔 매핑 파일이 있으면 API 호출 없이 재사용
    if os.path.exists(MAPPING_PATH):
        with open(MAPPING_PATH, encoding="utf-8") as f:
            mapping = json.load(f)
        print("기존 매핑 재사용 (API 호출 없음)")
    else:
        values = collect_values(df)
        total_uniques = sum(len(c) for c in values.values())
        print(f"정규화 대상: {len(values)}개 축, 고유 값 {total_uniques}개 → Gemini 1회 호출")
        mapping = build_mapping(values)

    # 검수 결과 반영: 잘못 묶인 매핑을 수동 교정
    for axis, fixes in MANUAL_OVERRIDES.items():
        mapping.setdefault(axis, {}).update(fixes)
    codebook = build_codebook(df, mapping)

    # 저장: 코드북(번호→레이블), 매핑(원시값→레이블), 코드 부여된 리뷰 테이블
    with open(CODEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(codebook, f, ensure_ascii=False, indent=2)
    with open(MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    coded = apply_codes(df, mapping, codebook)
    coded.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    print(f"\n코드북 저장: {CODEBOOK_PATH}")
    for axis, codes in codebook.items():
        print(f"  {axis}: {codes}")
    print(f"매핑 저장: {MAPPING_PATH}")
    print(f"코드 부여 테이블 저장: {OUT_PATH}")
