# -*- coding: utf-8 -*-
"""원본 수집 CSV + 리뷰수 보정 jsonl → data/*.csv 집계 7개.

1단계 스크립트. 원본 데이터가 있어야 실행된다(저장소에는 미포함).
원본 경로는 --src 로 지정하며 기본값은 개발자 로컬 경로다.

    python make_aggregates.py --src "C:/Users/daemi/OneDrive/바탕 화면/kurly_kidswear"
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

from analyze_kurly import classify, etc_group

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
DEFAULT_SRC = r"C:/Users/daemi/OneDrive/바탕 화면/kurly_kidswear"

PRICE_CUT = 20000
PRICE_LO, PRICE_HI = "2만원 미만", "2만원 이상"


def load_corrected(src):
    """원본 CSV 를 읽고 리뷰수 보정을 적용한다.

    목록 API 는 리뷰가 적은 상품의 review_count 를 0 으로 반환한다.
    enrich_reviews.py 가 상세 API 로 재확인한 값이 jsonl 에 있으므로,
    원본이 0 인 행만 그 값으로 대체한다(analyze_kurly.py:182-196 과 동일).
    """
    csvs = sorted(glob.glob(os.path.join(src, "kurly_kidswear_*.csv")))
    if not csvs:
        raise SystemExit(f"원본 CSV 없음: {src}")
    df = pd.read_csv(csvs[-1], encoding="utf-8-sig")

    jsonls = sorted(glob.glob(os.path.join(src, "review_counts_*.jsonl")))
    if not jsonls:
        raise SystemExit(f"보정 jsonl 없음: {src}. enrich_reviews.py 를 먼저 실행하세요.")
    fx = pd.read_json(jsonls[-1], lines=True)
    fx = fx[fx["status"].eq("ok") & fx["review_count"].notna()]
    m = dict(zip(fx["no"].astype(int), fx["review_count"].astype(int)))

    before = int(df["리뷰수"].sum())
    df["리뷰수"] = df.apply(
        lambda r: m.get(int(r["상품ID"]), r["리뷰수"]) if r["리뷰수"] == 0 else r["리뷰수"],
        axis=1).astype(int)
    after = int(df["리뷰수"].sum())
    print(f"리뷰수 보정: {before:,} -> {after:,}")
    if after != 2498:
        raise SystemExit(f"보정 후 총리뷰가 2,498 이 아닙니다({after:,}). 원본 스냅샷을 확인하세요.")

    df["품목"] = df["상품명"].map(classify)
    df["가격대"] = np.where(df["판매가"] < PRICE_CUT, PRICE_LO, PRICE_HI)
    return df


def gini(x):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def write_meta(df):
    rv = df["리뷰수"].to_numpy()
    pd.DataFrame([{
        "n_sku": len(df),
        "n_reviews": int(rv.sum()),
        "n_brands": int(df["브랜드명"].nunique()),
        "n_reviewed_sku": int((rv > 0).sum()),
        "n_zero_sku": int((rv == 0).sum()),
        # 4자리로 저장하면 0.94447 -> 0.9445 가 되고, 이를 다시 3자리로 읽을 때
        # 0.945 가 나와 리포트 표기(0.944)와 어긋난다. 이중 반올림을 피해 6자리로 둔다.
        "gini": round(gini(rv), 6),
        "snapshot": "20260728_161036",
    }]).to_csv(os.path.join(DATA, "meta.csv"), index=False, encoding="utf-8-sig")


def write_pareto(df):
    rv = np.sort(df["리뷰수"].to_numpy())[::-1]
    tot = int(rv.sum())
    rows = []
    for pct in (1, 5, 10, 20, 50):
        k = max(1, int(round(len(rv) * pct / 100)))   # ceil 금지 — 리포트와 어긋난다
        rows.append({"상위": f"{pct}%", "SKU수": k, "누적리뷰": int(rv[:k].sum()),
                     "리뷰점유율%": round(rv[:k].sum() / tot * 100, 1)})
    pd.DataFrame(rows).to_csv(os.path.join(DATA, "pareto.csv"),
                              index=False, encoding="utf-8-sig")


def write_delivery(df):
    c = (df.assign(리뷰0=df["리뷰수"].eq(0))
           .groupby("배송타입")
           .agg(SKU수=("상품ID", "count"), 리뷰0_SKU=("리뷰0", "sum"),
                총리뷰수=("리뷰수", "sum"), 중앙값리뷰=("리뷰수", "median")))
    c["리뷰0_비율%"] = (c["리뷰0_SKU"] / c["SKU수"] * 100).round(1)
    c["리뷰per_SKU"] = (c["총리뷰수"] / c["SKU수"]).round(2)
    c.to_csv(os.path.join(DATA, "delivery.csv"), encoding="utf-8-sig")


def write_brand(df):
    a = (df.groupby("브랜드명")
           .agg(SKU수=("상품ID", "count"), 총리뷰수=("리뷰수", "sum"),
                평균가격=("판매가", "mean"))
           .assign(리뷰per_SKU=lambda x: (x["총리뷰수"] / x["SKU수"]).round(2))
           .sort_values("총리뷰수", ascending=False))
    a["평균가격"] = a["평균가격"].round().astype(int)
    a[["SKU수", "총리뷰수", "리뷰per_SKU", "평균가격"]].to_csv(
        os.path.join(DATA, "brand.csv"), encoding="utf-8-sig")


def write_category(df):
    d = (df.groupby("품목")
           .agg(SKU수=("상품ID", "count"), 총리뷰수=("리뷰수", "sum"),
                평균가격=("판매가", "mean")))
    d["SKU비중%"] = (d["SKU수"] / len(df) * 100).round(1)
    d["리뷰비중%"] = (d["총리뷰수"] / df["리뷰수"].sum() * 100).round(1)
    d["리뷰밀도"] = (d["총리뷰수"] / d["SKU수"]).round(2)
    d["평균가격"] = d["평균가격"].round().astype(int)
    d = d[["SKU수", "SKU비중%", "총리뷰수", "리뷰비중%", "리뷰밀도", "평균가격"]]
    d.sort_values("총리뷰수", ascending=False).to_csv(
        os.path.join(DATA, "category.csv"), encoding="utf-8-sig")


def _cross(df, index):
    """index × 배송타입 교차표를 SKU_/리뷰_ 접두사로 평탄화한다."""
    t = df.pivot_table(index=index, columns="배송타입", values="상품ID",
                       aggfunc="count", fill_value=0).add_prefix("SKU_")
    r = df.pivot_table(index=index, columns="배송타입", values="리뷰수",
                       aggfunc="sum", fill_value=0).add_prefix("리뷰_")
    return pd.concat([t, r], axis=1)


def write_category_delivery(df):
    x = _cross(df, "품목")
    for dv in ("샛별배송", "판매자배송"):
        x[f"밀도_{dv}"] = (x[f"리뷰_{dv}"] / x[f"SKU_{dv}"]).round(2)
    x.to_csv(os.path.join(DATA, "category_delivery.csv"), encoding="utf-8-sig")


def write_price_delivery(df):
    x = _cross(df, "가격대")
    for dv in ("샛별배송", "판매자배송"):
        x[f"밀도_{dv}"] = (x[f"리뷰_{dv}"] / x[f"SKU_{dv}"]).round(2)
    x.to_csv(os.path.join(DATA, "price_delivery.csv"), encoding="utf-8-sig")


def write_brand_delivery(df):
    """샛별·판매자 양쪽에 상품이 있는 브랜드만. 2막의 브랜드 내 자연실험 근거다."""
    x = _cross(df, "브랜드명")
    both = x[(x["SKU_샛별배송"] > 0) & (x["SKU_판매자배송"] > 0)].copy()
    for dv in ("샛별배송", "판매자배송"):
        both[f"밀도_{dv}"] = (both[f"리뷰_{dv}"] / both[f"SKU_{dv}"]).round(2)
    price = df.pivot_table(index="브랜드명", columns="배송타입", values="판매가",
                           aggfunc="mean").round().astype("Int64").add_prefix("평균가_")
    both = both.join(price, how="left")
    both.sort_values("리뷰_샛별배송", ascending=False).to_csv(
        os.path.join(DATA, "brand_delivery.csv"), encoding="utf-8-sig")


def write_category_etc(df):
    """'기타' 1,718건의 세부 구성. 제안 ②(시즌 기획전)의 근거다."""
    etc = df[df["품목"] == "기타"].copy()
    etc["세부"] = etc["상품명"].map(etc_group)
    e = (etc.groupby("세부")
            .agg(SKU수=("상품ID", "count"), 총리뷰수=("리뷰수", "sum"),
                 평균가격=("판매가", "mean")))
    e["평균가격"] = e["평균가격"].round().astype(int)
    e.sort_values("SKU수", ascending=False).to_csv(
        os.path.join(DATA, "category_etc.csv"), encoding="utf-8-sig")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC, help="원본 데이터 폴더")
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    df = load_corrected(args.src)
    write_meta(df)
    write_pareto(df)
    write_delivery(df)
    write_brand(df)
    write_category(df)
    write_category_delivery(df)
    write_price_delivery(df)
    write_brand_delivery(df)
    write_category_etc(df)
    print(f"완료. {DATA} 에 CSV 9개 생성")


if __name__ == "__main__":
    main()
