# -*- coding: utf-8 -*-
"""
컬리 카테고리 상품 수집기.

주신 _next/data URL은 카테고리 메타(하위 카테고리/정렬옵션)만 반환하고
상품은 들어있지 않습니다. 실제 상품 목록은 JS 번들에서 확인한 아래 엔드포인트입니다.

    GET https://api.kurly.com/collection/v2/home/sites/{site}/product-categories/{code}/products
        ?sort_type=&page=&per_page=&filters=

번들 근거 (chunks/01pbwlxzm8mkl.js):
    let u = e => `/collection/v2/home/sites/${e.toLowerCase()}`
    h = `${u(d)}/product-${t}/${r}/products?sort_type=${n}&page=${o}&per_page=${l}&filters=${p}`

사용법:
    python collect_kurly.py            # 새 수집 (raw/<타임스탬프>/ 생성)
    python collect_kurly.py --resume   # 최신 raw 디렉터리 재사용, 없는 페이지만 요청
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

import pandas as pd
import requests

# ---------------------------------------------------------------- 설정
API = "https://api.kurly.com/collection/v2/home/sites/{site}/product-categories/{code}/products"

CATEGORIES = {
    "172": "키즈웨어",
    "919017": "유아동패션",
}

SITE = "market"
PER_PAGE = 96          # PC 기본값 (번들 getDefaultPerPage: categories=96)
SORT_TYPE = 0          # 0=신상품순. 등록일 기준이라 페이지네이션이 가장 안정적
FILTERS = ""           # 전체 수집 (delivery_type 필터 걸지 않음)

SLEEP = 1.0            # 요청 간 대기
RETRIES = 3            # 실패 시 재시도 횟수
TIMEOUT = 30

BASE = os.path.dirname(os.path.abspath(__file__))
RAW_ROOT = os.path.join(BASE, "raw")

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "origin": "https://www.kurly.com",
    "referer": "https://www.kurly.com/categories/172?page=1&per_page=96&sorted_type=1",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
}


# ---------------------------------------------------------------- 수집
def fetch(session, code, page):
    """한 페이지 요청. 3회까지 지수 백오프 재시도."""
    url = API.format(site=SITE, code=code)
    params = {"sort_type": SORT_TYPE, "page": page,
              "per_page": PER_PAGE, "filters": FILTERS}

    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:150]}"
        except Exception as e:                                  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"

        if attempt < RETRIES:
            back = SLEEP * (2 ** attempt)
            print(f"      재시도 {attempt}/{RETRIES - 1} ({last}) — {back:.0f}s 후", flush=True)
            time.sleep(back)

    raise RuntimeError(f"cat={code} page={page} {RETRIES}회 실패 — {last}")


def collect(raw_dir):
    """카테고리별 전 페이지 순회. 이미 저장된 페이지는 요청하지 않음."""
    os.makedirs(raw_dir, exist_ok=True)
    session = requests.Session()
    stats = {}

    for code, label in CATEGORIES.items():
        print(f"\n[{code}] {label}")
        page, total_pages, got, reused = 1, None, 0, 0

        while total_pages is None or page <= total_pages:
            path = os.path.join(raw_dir, f"cat{code}_p{page:03d}.json")

            if os.path.exists(path):                            # 재수집 방지
                payload = json.load(open(path, encoding="utf-8"))
                reused += 1
            else:
                payload = fetch(session, code, page)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False)
                time.sleep(SLEEP)

            pg = payload.get("meta", {}).get("pagination", {})
            if total_pages is None:
                total_pages = pg.get("total_pages", 1)
                print(f"  총 {pg.get('total'):,}건 / {total_pages}페이지")

            got += len(payload.get("data") or [])
            print(f"  p{page:>3}/{total_pages}  누적 {got:,}건"
                  f"{'  (기존 파일 재사용)' if os.path.exists(path) and reused else ''}",
                  flush=True)
            page += 1

        stats[code] = {"label": label, "pages": total_pages,
                       "items": got, "reported_total": pg.get("total")}
        print(f"  완료: {got:,}건 (재사용 {reused}p)")

    return stats


# ---------------------------------------------------------------- 파싱
BRACKET = re.compile(r"^\s*\[([^\]]+)\]\s*")


def brand_of(name):
    """상품명 '[브랜드] 상품' 접두사에서 브랜드 추출 (목록 API에 브랜드 필드 없음)."""
    m = BRACKET.match(name or "")
    return m.group(1).strip() if m else None


def delivery_of(infos):
    """delivery_type_infos -> 샛별배송 / 판매자배송.

    DAWN 이 하나라도 있으면 샛별로 본다 (컬리 직배송).
    """
    types = {d.get("type") for d in (infos or [])}
    if not types:
        return "미상"
    if "DAWN" in types:
        return "샛별배송"
    if "NORMAL_PARCEL" in types:
        return "판매자배송"
    return "/".join(sorted(t for t in types if t))


def to_frame(raw_dir):
    rows, seen = [], set()

    for code, label in CATEGORIES.items():
        files = sorted(f for f in os.listdir(raw_dir)
                       if f.startswith(f"cat{code}_p") and f.endswith(".json"))
        for fn in files:
            payload = json.load(open(os.path.join(raw_dir, fn), encoding="utf-8"))
            for p in payload.get("data") or []:
                key = (code, p["no"])
                if key in seen:                    # 페이지 경계 중복 방어
                    continue
                seen.add(key)

                sales = p.get("sales_price")
                disc = p.get("discounted_price")
                rows.append({
                    "category": f"{code}_{label}",
                    "상품ID": p.get("no"),
                    "상품명": p.get("name"),
                    "브랜드명": brand_of(p.get("name")),
                    "정가": sales,
                    "판매가": disc if disc else sales,
                    "할인율": p.get("discount_rate"),
                    "배송타입": delivery_of(p.get("delivery_type_infos")),
                    "리뷰수": pd.to_numeric(p.get("review_count"), errors="coerce"),
                    # 컬리 API는 별점을 제공하지 않음 (상세 API에도 rating/score/star 키 없음)
                    "평점": pd.NA,
                    "품절여부": p.get("is_sold_out"),
                })

    df = pd.DataFrame(rows)
    df["리뷰수"] = df["리뷰수"].fillna(0).astype(int)
    df["평점"] = df["평점"].astype("Float64")
    return df


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true",
                    help="가장 최근 raw 디렉터리를 재사용해 없는 페이지만 요청")
    args = ap.parse_args()

    os.makedirs(RAW_ROOT, exist_ok=True)
    existing = sorted(d for d in os.listdir(RAW_ROOT)
                      if os.path.isdir(os.path.join(RAW_ROOT, d)))

    if args.resume and existing:
        ts = existing[-1]
        print(f"재사용: raw/{ts}")
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"신규 수집: raw/{ts}")

    raw_dir = os.path.join(RAW_ROOT, ts)
    stats = collect(raw_dir)

    df = to_frame(raw_dir)
    out = os.path.join(BASE, f"kurly_kidswear_{ts}.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print(f"CSV 저장: {os.path.basename(out)}  ({len(df):,}행)")
    for code, s in stats.items():
        n = (df["category"] == f"{code}_{s['label']}").sum()
        flag = "" if n == s["reported_total"] else f"  <- API 신고값 {s['reported_total']:,}"
        print(f"  {code} {s['label']}: {n:,}건{flag}")
    print(f"원본 JSON: raw/{ts}/ ({len(os.listdir(raw_dir))} 파일)")

    with open(os.path.join(raw_dir, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"collected_at": ts, "endpoint": API, "site": SITE,
                   "per_page": PER_PAGE, "sort_type": SORT_TYPE,
                   "filters": FILTERS, "stats": stats}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
