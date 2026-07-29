# -*- coding: utf-8 -*-
"""data/*.csv → payload → output/kidswear_diagnosis.html.

2단계 스크립트. 커밋된 data/ 만 읽으므로 원본 없이도 실행된다.
"""
import os

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "output", "kidswear_diagnosis.html")

SEASONAL_ETC = ["한복", "파티·이벤트용품", "수영"]   # category_etc.csv 에 있는 것
SEASONAL_MAIN = ["아우터"]                            # category.csv 에 있는 것
PROPOSAL1_ITEMS = ["잠옷", "장화", "샌들"]


def _read(name, index_col=0):
    return pd.read_csv(os.path.join(DATA, name), encoding="utf-8-sig",
                       index_col=index_col)


def build_payload():
    meta_row = _read("meta.csv", index_col=None).iloc[0]
    pareto = _read("pareto.csv")
    delivery = _read("delivery.csv")
    brand = _read("brand.csv")
    category = _read("category.csv")
    cat_dv = _read("category_delivery.csv")
    price_dv = _read("price_delivery.csv")
    brand_dv = _read("brand_delivery.csv")
    cat_etc = _read("category_etc.csv")

    meta = {
        "n_sku": int(meta_row["n_sku"]),
        "n_reviews": int(meta_row["n_reviews"]),
        "n_brands": int(meta_row["n_brands"]),
        "n_reviewed_sku": int(meta_row["n_reviewed_sku"]),
        "n_zero_sku": int(meta_row["n_zero_sku"]),
        "gini": float(meta_row["gini"]),
        "snapshot": str(meta_row["snapshot"]),
        "reviewed_share": round(int(meta_row["n_reviewed_sku"])
                                / int(meta_row["n_sku"]) * 100, 1),
        "top1pct_share": float(pareto.loc["1%", "리뷰점유율%"]),
    }

    payload = {
        "meta": meta,
        "pareto": [{"label": i, "sku": int(r["SKU수"]), "cum": int(r["누적리뷰"]),
                    "share": float(r["리뷰점유율%"])}
                   for i, r in pareto.iterrows()],
        "delivery": [{"type": i, "sku": int(r["SKU수"]),
                      "zero_sku": int(r["리뷰0_SKU"]), "zero_pct": float(r["리뷰0_비율%"]),
                      "reviews": int(r["총리뷰수"]), "density": float(r["리뷰per_SKU"])}
                     for i, r in delivery.iterrows()],
        "brand": [{"brand": i, "sku": int(r["SKU수"]), "reviews": int(r["총리뷰수"]),
                   "density": float(r["리뷰per_SKU"]), "price": int(r["평균가격"])}
                  for i, r in brand.iterrows()],
        "category": [{"item": i, "sku": int(r["SKU수"]), "sku_share": float(r["SKU비중%"]),
                      "reviews": int(r["총리뷰수"]), "review_share": float(r["리뷰비중%"]),
                      "density": float(r["리뷰밀도"]), "price": int(r["평균가격"])}
                     for i, r in category.iterrows()],
        "category_delivery": [{"item": i,
                               "dawn_sku": int(r["SKU_샛별배송"]),
                               "dawn_reviews": int(r["리뷰_샛별배송"]),
                               "seller_sku": int(r["SKU_판매자배송"]),
                               "seller_reviews": int(r["리뷰_판매자배송"])}
                              for i, r in cat_dv.iterrows()],
        "price_delivery": [{"price": i, "delivery": dv,
                            "sku": int(r[f"SKU_{dv}"]),
                            "reviews": int(r[f"리뷰_{dv}"]),
                            "density": float(r[f"밀도_{dv}"])}
                           for i, r in price_dv.iterrows()
                           for dv in ("샛별배송", "판매자배송")],
        "brand_delivery": [{"brand": i,
                            "dawn_sku": int(r["SKU_샛별배송"]),
                            "dawn_reviews": int(r["리뷰_샛별배송"]),
                            "dawn_density": float(r["밀도_샛별배송"]),
                            "dawn_price": int(r["평균가_샛별배송"]),
                            "seller_sku": int(r["SKU_판매자배송"]),
                            "seller_reviews": int(r["리뷰_판매자배송"]),
                            "seller_density": float(r["밀도_판매자배송"]),
                            "seller_price": int(r["평균가_판매자배송"])}
                           for i, r in brand_dv.iterrows()],
        "category_etc": [{"item": i, "sku": int(r["SKU수"]),
                          "reviews": int(r["총리뷰수"]), "price": int(r["평균가격"])}
                         for i, r in cat_etc.iterrows()],
    }
    payload["derived"] = _derive(payload, cat_dv, category, cat_etc)
    return payload


def _density(reviews, sku):
    return round(reviews / sku, 2) if sku else 0.0


def _derive(payload, cat_dv, category, cat_etc):
    """대시보드가 직접 주장하는 파생 지표. 여기서 한 번만 계산한다."""
    dawn_lift = []
    for item in ("실내화", "학용품"):
        r = cat_dv.loc[item]
        seller = _density(r["리뷰_판매자배송"], r["SKU_판매자배송"])
        dawn = _density(r["리뷰_샛별배송"], r["SKU_샛별배송"])
        dawn_lift.append({
            "item": item,
            "seller_sku": int(r["SKU_판매자배송"]), "seller_reviews": int(r["리뷰_판매자배송"]),
            "seller_density": seller,
            "dawn_sku": int(r["SKU_샛별배송"]), "dawn_reviews": int(r["리뷰_샛별배송"]),
            "dawn_density": dawn,
            "multiple": round(dawn / seller, 1),
        })

    proposal1 = []
    for item in PROPOSAL1_ITEMS:
        r = cat_dv.loc[item]
        proposal1.append({
            "item": item,
            "dawn_sku": int(r["SKU_샛별배송"]),
            "seller_sku": int(r["SKU_판매자배송"]),
            "seller_reviews": int(r["리뷰_판매자배송"]),
            "seller_density": _density(r["리뷰_판매자배송"], r["SKU_판매자배송"]),
        })

    rows = []
    for item in SEASONAL_ETC:
        r = cat_etc.loc[item]
        rows.append({"item": item, "sku": int(r["SKU수"]), "reviews": int(r["총리뷰수"])})
    for item in SEASONAL_MAIN:
        r = category.loc[item]
        rows.append({"item": item, "sku": int(r["SKU수"]), "reviews": int(r["총리뷰수"])})
    rows.sort(key=lambda x: -x["sku"])
    total_sku = sum(r["sku"] for r in rows)
    total_reviews = sum(r["reviews"] for r in rows)
    seasonal = {
        "rows": rows,
        "total_sku": total_sku,
        "total_reviews": total_reviews,
        "sku_share": round(total_sku / payload["meta"]["n_sku"] * 100, 1),
        "review_share": round(total_reviews / payload["meta"]["n_reviews"] * 100, 1),
    }
    return {"dawn_lift": dawn_lift, "proposal1": proposal1, "seasonal": seasonal}
