# -*- coding: utf-8 -*-
"""
컬리 리뷰 속성 → 코드북 구축 (2단계)

1단계에서 추출한 kurly_attributes_full.csv의 속성값을 정규화(동의어 통합)한 뒤,
축(핏/사이즈감/...)마다 값→숫자코드 매핑표(코드북)를 만든다.
API 호출 없음 — 전부 로컬 집계.

산출물:
- data/codebook_kurly.json          : {"축": {"1": "값", ...}}
- data/codebook_mapping_kurly.json  : {"축": {"원본값": "정규화값", ...}}  (정정된 값만 기록)
- data/kurly_attributes_coded.csv   : 원본 + 각 축의 코드 컬럼(_code) 추가
"""

import json
import os

import pandas as pd

DATA_DIR = "data"
IN_PATH = os.path.join(DATA_DIR, "kurly_attributes_full.csv")
OUT_CODEBOOK = os.path.join(DATA_DIR, "codebook_kurly.json")
OUT_MAPPING = os.path.join(DATA_DIR, "codebook_mapping_kurly.json")
OUT_CODED = os.path.join(DATA_DIR, "kurly_attributes_coded.csv")

AXES = ["핏", "사이즈감", "기장", "비침", "두께", "신축성", "착용상황", "계절감", "감성"]

# 1단계 추출 결과를 훑어보니 프롬프트의 통제 어휘를 대부분 따랐지만,
# 아래처럼 축을 벗어난 값이나 복수값이 소수 섞여 있었다. 여기서 정규화한다.
# (키: 원본값 → 값: 정규화값. 정규화값이 None이면 해당 값은 결측 처리)
MANUAL_FIXES = {
    "착용상황": {
        "출근": "오피스",                  # 오피스와 같은 의미
        "여름": None,                      # 계절감 축의 값이 잘못 들어온 경우 → 결측 처리
        "홈웨어, 외출·나들이": "홈웨어",     # 복수값은 첫 번째 값으로 단순화
    },
    "계절감": {
        "봄": "간절기",
        "가을": "간절기",
    },
}


def normalize(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """MANUAL_FIXES를 적용하고, 실제로 값이 바뀐 항목만 매핑 로그로 남긴다."""
    applied = {}
    for axis, fixes in MANUAL_FIXES.items():
        if axis not in df.columns:
            continue
        mask = df[axis].isin(fixes.keys())
        if mask.any():
            applied.setdefault(axis, {})
            for orig, new in fixes.items():
                cnt = (df[axis] == orig).sum()
                if cnt:
                    applied[axis][orig] = new
            df[axis] = df[axis].replace(fixes)
    return df, applied


def build_codebooks(df: pd.DataFrame) -> dict:
    """축마다 등장하는 값을 빈도 내림차순으로 정렬해 '1'부터 번호를 매긴다."""
    codebook = {}
    for axis in AXES:
        counts = df[axis].value_counts()  # NaN은 자동 제외
        codebook[axis] = {str(i + 1): v for i, v in enumerate(counts.index)}
    return codebook


def apply_codes(df: pd.DataFrame, codebook: dict) -> pd.DataFrame:
    """각 축에 대해 값→코드 역매핑을 만들어 '_code' 컬럼을 추가한다."""
    for axis in AXES:
        value_to_code = {v: k for k, v in codebook[axis].items()}
        df[f"{axis}_code"] = df[axis].map(value_to_code)  # 결측은 NaN 유지
    return df


def main():
    df = pd.read_csv(IN_PATH)
    print(f"입력: {len(df)}건 로드")

    df, applied = normalize(df)
    print("\n■ 정규화 적용 내역 (원본값 -> 정규화값, 건수)")
    for axis, fixes in applied.items():
        for orig, new in fixes.items():
            cnt = (df[axis] == new).sum() if new else None
            print(f"  [{axis}] '{orig}' -> {new!r}")

    codebook = build_codebooks(df)
    print("\n■ 축별 코드북 (값: 빈도 내림차순)")
    for axis, mapping in codebook.items():
        print(f"  {axis}: {mapping}")

    df = apply_codes(df, codebook)

    with open(OUT_CODEBOOK, "w", encoding="utf-8") as f:
        json.dump(codebook, f, ensure_ascii=False, indent=2)
    with open(OUT_MAPPING, "w", encoding="utf-8") as f:
        json.dump(applied, f, ensure_ascii=False, indent=2)
    df.to_csv(OUT_CODED, index=False, encoding="utf-8-sig")

    print(f"\n저장 완료:\n  {OUT_CODEBOOK}\n  {OUT_MAPPING}\n  {OUT_CODED}")


if __name__ == "__main__":
    main()
