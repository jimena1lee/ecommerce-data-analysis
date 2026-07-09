# -*- coding: utf-8 -*-
"""
상품별 Semantic ID 부여 (3단계)

kurly_attributes_coded.csv를 상품(Product Name) 단위로 집계해서,
각 속성 축의 최빈값(mode)을 그 상품의 대표 속성으로 삼고
"핏1-사2-계1..." 형태의 Semantic ID 문자열을 만든다.
API 호출 없음 — 전부 로컬 집계.

컬리 리뷰에는 별점이 없으므로, 무신사 버전의 '평균평점' 대신
감성(만족/불만/중립) 집계로 반품·불만 리스크를 대체 지표화한다.

산출물: data/kurly_product_semantic_ids.csv
"""

import json
import os

import pandas as pd

DATA_DIR = "data"
IN_PATH = os.path.join(DATA_DIR, "kurly_attributes_coded.csv")
CODEBOOK_PATH = os.path.join(DATA_DIR, "codebook_kurly.json")
OUT_PATH = os.path.join(DATA_DIR, "kurly_product_semantic_ids.csv")

# 감성은 리스크 지표로 따로 다루므로 Semantic ID 조합 축에서는 제외한다
ID_AXES = ["핏", "사이즈감", "기장", "비침", "두께", "신축성", "착용상황", "계절감"]
ABBR = {"핏": "핏", "사이즈감": "사", "기장": "기", "비침": "비",
        "두께": "두", "신축성": "신", "착용상황": "착", "계절감": "계"}


def mode_with_ratio(series: pd.Series):
    """결측을 제외한 값 중 최빈값과 '최빈값건수/전체non-null건수'를 함께 반환."""
    s = series.dropna()
    if s.empty:
        return None, None, 0
    counts = s.value_counts()
    top_val = counts.index[0]
    return top_val, f"{top_val}({counts.iloc[0]}/{len(s)})", len(s)


def main():
    df = pd.read_csv(IN_PATH)
    codebook = json.load(open(CODEBOOK_PATH, encoding="utf-8"))
    value_to_code = {axis: {v: k for k, v in m.items()} for axis, m in codebook.items()}

    rows = []
    for product, g in df.groupby("Product Name"):
        row = {"Product Name": product, "카테고리": g["category"].iloc[0], "리뷰수": len(g)}

        # 감성(만족/불만/중립) 집계 → 반품·불만 리스크 대체 지표
        sentiment_counts = g["감성"].value_counts()
        n_bad = int(sentiment_counts.get("불만", 0))
        row["불만리뷰수"] = n_bad
        row["불만비율"] = round(n_bad / len(g), 2)

        id_parts = []
        n_assigned = 0
        for axis in ID_AXES:
            val, display, n_valid = mode_with_ratio(g[axis])
            row[axis] = display
            if val is not None:
                code = value_to_code[axis][val]
                row[f"{axis}_code"] = code
                id_parts.append(f"{ABBR[axis]}{code}")
                n_assigned += 1
            else:
                row[f"{axis}_code"] = None

        row["semantic_id"] = "-".join(id_parts)
        row["부여_축_수"] = n_assigned
        rows.append(row)

    out = pd.DataFrame(rows).sort_values("리뷰수", ascending=False).reset_index(drop=True)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    print(f"상품 {len(out)}개에 Semantic ID 부여 완료 -> {OUT_PATH}")
    print(f"\n리뷰 많은 상품 TOP 5:")
    print(out[["Product Name", "리뷰수", "불만비율", "semantic_id", "부여_축_수"]].head(5).to_string(index=False))
    print(f"\n불만비율 높은 상품 TOP 5 (리뷰 5건 이상):")
    risky = out[out["리뷰수"] >= 5].sort_values("불만비율", ascending=False)
    print(risky[["Product Name", "리뷰수", "불만리뷰수", "불만비율", "semantic_id"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
