# -*- coding: utf-8 -*-
"""
상품별 Semantic ID 부여 스크립트 (3단계)

2단계에서 코드가 부여된 리뷰 테이블(attributes_coded.csv)을 상품 단위로 집계해,
상품마다 대표 속성 조합 코드(Semantic ID)를 만듭니다.

로직:
  - 상품별 × 축별로 리뷰에서 가장 많이 언급된 코드(최빈값)를 대표 코드로 선정
  - 단, 언급이 2회 미만이면 신뢰도가 낮으므로 대표 코드를 부여하지 않음 (- 처리)
  - Semantic ID 표기: 핏2-착1-사3 처럼 "축약어+코드" 조합 문자열

API 호출 없음. 실행: python assign_semantic_id.py
"""

import io
import json
import os
import sys

import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.path.dirname(__file__)
IN_PATH = os.path.join(BASE, "data", "attributes_coded.csv")
CODEBOOK_PATH = os.path.join(BASE, "data", "codebook_026.json")
OUT_PATH = os.path.join(BASE, "data", "product_semantic_ids.csv")

MIN_MENTIONS = 2  # 대표 코드로 인정할 최소 언급 횟수

# Semantic ID 문자열에 쓸 축 약어 (읽기 좋게 한 글자)
AXIS_SHORT = {
    "핏": "핏", "착용감": "착", "사이즈감": "사", "기장": "장", "비침": "비",
    "두께": "두", "신축성": "신", "촉감": "촉", "계절감": "계",
}


def top_code(series: pd.Series):
    """축 하나에 대해 상품의 대표 코드를 뽑습니다. 언급 부족 시 None."""
    counts = series.dropna().value_counts()
    if len(counts) == 0 or counts.iloc[0] < MIN_MENTIONS:
        return None, 0, 0
    # (대표 코드, 해당 코드 언급 수, 축 전체 언급 수)
    return counts.index[0], int(counts.iloc[0]), int(counts.sum())


if __name__ == "__main__":
    df = pd.read_csv(IN_PATH, encoding="utf-8-sig")
    with open(CODEBOOK_PATH, encoding="utf-8") as f:
        codebook = json.load(f)
    axes = list(codebook.keys())

    rows = []
    for product, g in df.groupby("Product Name"):
        row = {"Product Name": product, "리뷰수": len(g), "평균평점": round(g["Rating"].mean(), 2)}
        id_parts = []
        for axis in axes:
            # 코드 컬럼은 숫자로 읽힐 수 있어 문자열로 통일
            code, hits, total = top_code(g[f"{axis}_code"].astype("string"))
            if code is not None:
                code = str(int(float(code)))  # "2.0" → "2"
                label = codebook[axis][code]
                row[axis] = f"{label}({hits}/{total})"   # 사람이 읽는 용도: 레이블(지지수/전체언급수)
                row[f"{axis}_code"] = code
                id_parts.append(f"{AXIS_SHORT[axis]}{code}")
            else:
                row[axis] = None
                row[f"{axis}_code"] = None
        row["semantic_id"] = "-".join(id_parts) if id_parts else None
        row["부여_축_수"] = len(id_parts)
        rows.append(row)

    out = pd.DataFrame(rows).sort_values("부여_축_수", ascending=False)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    print(f"상품 {len(out)}개에 Semantic ID 부여 완료 → {OUT_PATH}")
    print(f"축 2개 이상 부여된 상품: {(out['부여_축_수'] >= 2).sum()}개")
    print(f"부여 실패(리뷰 부족) 상품: {(out['부여_축_수'] == 0).sum()}개")
    print("\n=== 예시 (부여 축 많은 순 상위 10개) ===")
    for _, r in out.head(10).iterrows():
        print(f"- {r['Product Name'][:30]} | {r['semantic_id']} (리뷰 {r['리뷰수']}건)")
