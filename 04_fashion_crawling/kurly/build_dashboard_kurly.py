# -*- coding: utf-8 -*-
"""
컬리 리뷰 인사이트 대시보드 빌더.

kurly/data/의 수집·태깅 결과(CSV·코드북)를 읽어 통계를 미리 계산하고,
dashboard_template.html의 /*__PAYLOAD__*/ 자리에 JSON으로 심어
자기완결 정적 HTML(output/dashboard.html)을 만든다.

- 런타임 서버·AI 호출 없음: 유사도 계산·차트는 내장 JS가 브라우저에서 수행
- 실행:  cd kurly && python build_dashboard_kurly.py
- 검증:  python -m pytest test_dashboard_payload.py -q
"""

import glob
import json
import os
from collections import Counter

import pandas as pd

DATA_DIR = "data"
OUT_PATH = os.path.join("output", "dashboard.html")

CATS = {"165": "패션의류", "166": "신발·잡화", "169": "언더웨어·홈웨어"}
AXES = ["핏", "사이즈감", "기장", "비침", "두께", "신축성", "착용상황", "계절감"]

# 불만사유 유형화 — build_insight_report_kurly.py와 동일한 키워드 그룹
COMPLAINT_KEYWORDS = [
    ("사이즈 작음", ["작"]),
    ("사이즈/기장 큼", ["큼", "크게"]),
    ("배송 지연", ["배송"]),
    ("기장 짧음", ["기장", "짧"]),
    ("비침 있음", ["비침"]),
    ("색상 불만족", ["색상", "색깔"]),
    ("마감/봉제 불량", ["실밥", "봉제", "마감", "박음질"]),
    ("세탁 후 변형", ["수축", "변형", "세탁"]),
    ("소재/촉감 불만", ["촉감", "까슬", "답답", "무거움"]),
    ("디자인/핏 불만", ["디자인", "핏 불량", "싼티", "촌스러", "부해", "핏과"]),
    ("가격 대비 품질", ["가격", "품질"]),
    ("더움/불편", ["더움", "더워"]),
    ("말림/들뜸", ["말림", "말려", "들뜸"]),
]


def group_complaint(text: str) -> str:
    for label, keywords in COMPLAINT_KEYWORDS:
        if any(k in text for k in keywords):
            return label
    return "기타(개별 불만)"


def _parse_price(v) -> "int | None":
    n = pd.to_numeric(str(v).replace(",", "").strip(), errors="coerce")
    return None if pd.isna(n) else int(n)


def _parse_discount(v) -> "int | None":
    n = pd.to_numeric(str(v).replace("%", "").strip(), errors="coerce")
    return None if pd.isna(n) else int(n)


def _mentions(att_rows: pd.DataFrame) -> dict:
    """리뷰 묶음에서 축별 라벨 언급 수 dict (빈 축은 생략)."""
    out = {}
    for axis in AXES:
        vc = att_rows[axis].dropna().value_counts()
        if len(vc):
            out[axis] = {str(k): int(v) for k, v in vc.items()}
    return out


def _samples(att_rows: pd.DataFrame, limit: int = 3) -> list:
    """대표 리뷰 발췌 — 불만사유 있는 리뷰 → 속성 언급 많은 리뷰 순."""
    rows = att_rows.copy()
    rows["_axes_n"] = rows[AXES].notna().sum(axis=1)
    rows["_has_reason"] = rows["불만사유"].notna()
    rows = rows.sort_values(["_has_reason", "_axes_n"], ascending=False).head(limit)
    out = []
    for _, r in rows.iterrows():
        body = " ".join(str(r["Review Body"]).split())
        if len(body) > 140:
            body = body[:140] + "…"
        out.append({
            "t": body,
            "sent": r["감성"] if pd.notna(r["감성"]) else "중립",
            "reason": r["불만사유"] if pd.notna(r["불만사유"]) else None,
        })
    return out


def build_payload() -> dict:
    att = pd.read_csv(os.path.join(DATA_DIR, "kurly_attributes_coded.csv"))
    att["category"] = att["category"].astype(str)
    sem = pd.read_csv(os.path.join(DATA_DIR, "kurly_product_semantic_ids.csv"))
    sem["카테고리"] = sem["카테고리"].astype(str)
    codebook = json.load(open(os.path.join(DATA_DIR, "codebook_kurly.json"), encoding="utf-8"))

    catalog = pd.concat(
        [pd.read_csv(sorted(glob.glob(os.path.join(DATA_DIR, f"kurly_products_{c}_*.csv")))[-1])
         for c in CATS],
        ignore_index=True,
    ).drop_duplicates(subset=["_goods_no"])
    catalog["_price"] = catalog["Price"].map(_parse_price)
    catalog["_disc"] = catalog["Discount Rate"].map(_parse_discount)

    merged = sem.merge(
        catalog[["Product Name", "Brand", "_price"]], on="Product Name", how="left"
    )
    att_by_product = dict(tuple(att.groupby("Product Name")))

    # --- 상품 199개 ---
    products = []
    for _, r in merged.iterrows():
        name = r["Product Name"]
        rows = att_by_product.get(name, att.iloc[0:0])
        products.append({
            "name": name,
            "cat": r["카테고리"],
            "brand": r["Brand"] if pd.notna(r["Brand"]) else "",
            "price": None if pd.isna(r["_price"]) else int(r["_price"]),
            "review_n": int(r["리뷰수"]),
            "complaint_n": int(r["불만리뷰수"]),
            "sid": r["semantic_id"] if pd.notna(r["semantic_id"]) else "",
            "mentions": _mentions(rows),
            "samples": _samples(rows),
        })

    # --- 브랜드 (전체 카탈로그 기준 상품 3개 이상) ---
    brands = []
    for brand, cat_rows in catalog.groupby("Brand"):
        if len(cat_rows) < 3 or not str(brand).strip():
            continue
        rv = merged[merged["Brand"] == brand]          # 리뷰 데이터 있는 상품들
        names = set(rv["Product Name"])
        b_att = att[att["Product Name"].isin(names)]
        n_reviews = int(rv["리뷰수"].sum())
        n_complaints = int(rv["불만리뷰수"].sum())
        reasons = Counter(group_complaint(t) for t in b_att["불만사유"].dropna())
        size_vc = b_att["사이즈감"].dropna().value_counts()
        brands.append({
            "name": str(brand),
            "n_products": int(len(cat_rows)),
            "n_reviews": n_reviews,
            "avg_price": int(cat_rows["_price"].mean()) if cat_rows["_price"].notna().any() else None,
            "avg_discount": int(cat_rows["_disc"].mean()) if cat_rows["_disc"].notna().any() else None,
            "complaint_rate": round(n_complaints / n_reviews, 4) if n_reviews else None,
            "size": {str(k): int(v) for k, v in size_vc.items()},
            "mentions": _mentions(b_att),
            "reasons": [[k, int(v)] for k, v in reasons.most_common(3)],
            "cats": sorted({str(c) for c in cat_rows["Category"].map(
                lambda x: next((k for k, v in CATS.items() if v.replace("·", "") in str(x).replace("·", "")), None)) if c}
            ) or sorted({r2["카테고리"] for _, r2 in rv.iterrows()}),
            "products": [
                {"name": r2["Product Name"], "review_n": int(r2["리뷰수"]),
                 "complaint_n": int(r2["불만리뷰수"])}
                for _, r2 in rv.sort_values("리뷰수", ascending=False).iterrows()
            ],
        })
    brands.sort(key=lambda b: -b["n_products"])

    # --- 카테고리 통계 ---
    cat_stats = {}
    for cat in CATS:
        c_att = att[att["category"] == cat]
        c_sem = merged[merged["카테고리"] == cat]
        size_vc = c_att["사이즈감"].dropna().value_counts()
        cat_stats[cat] = {
            "n_products": int(len(c_sem)),
            "n_reviews": int(len(c_att)),
            "complaint_rate": round(c_sem["불만리뷰수"].sum() / c_sem["리뷰수"].sum(), 4),
            "avg_price": int(c_sem["_price"].mean()) if c_sem["_price"].notna().any() else None,
            "mentions": {axis: int(c_att[axis].notna().sum()) for axis in AXES},
            "size": {str(k): int(v) for k, v in size_vc.items()},
        }

    # --- 불만 유형 (유형 상위 10 + 기타) ---
    groups = Counter(group_complaint(t) for t in att["불만사유"].dropna())
    etc = groups.pop("기타(개별 불만)", 0)
    complaint_reasons = [[k, int(v)] for k, v in groups.most_common(10)]
    if etc:
        complaint_reasons.append(["기타(개별 불만)", int(etc)])

    return {
        "meta": {
            "built": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "n_products": len(products),
            "n_reviews": int(len(att)),
            "cats": CATS,
        },
        "axes": AXES,
        "codebook": {axis: [codebook[axis][k] for k in sorted(codebook[axis], key=int)]
                     for axis in AXES},
        "products": products,
        "brands": brands,
        "cat_stats": cat_stats,
        "complaint_reasons": complaint_reasons,
    }


def main():
    payload = build_payload()
    with open("dashboard_template.html", encoding="utf-8") as f:
        tpl = f.read()
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html_out = tpl.replace("/*__PAYLOAD__*/", "const DATA = " + js + ";")
    os.makedirs("output", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"생성 완료: {OUT_PATH} ({len(html_out) // 1024} KB)")


if __name__ == "__main__":
    main()
