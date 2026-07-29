# -*- coding: utf-8 -*-
"""목록 API의 review_count 보정.

검증 결과 목록 API(/collection/v2/.../products)의 review_count 는 리뷰가 적은
상품을 0으로 반환하는 경우가 있다 (예: 1001913098 목록 0 / 상세 2).
큰 값은 상세와 정확히 일치하므로, 목록에서 0 인 상품만 상세 API로 재확인한다.

    GET https://api.kurly.com/showroom/v2/products/{productCode}

결과는 review_counts_<ts>.jsonl 에 한 줄씩 적재 (중단 후 재실행하면 이어서 진행).
"""

import glob
import json
import os
import re
import sys
import time

import pandas as pd
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DETAIL = "https://api.kurly.com/showroom/v2/products/{no}"
SLEEP, RETRIES, TIMEOUT = 0.8, 3, 20

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "ko-KR,ko;q=0.9,en;q=0.8",
    "origin": "https://www.kurly.com",
    "referer": "https://www.kurly.com/",
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"),
}


def fetch(session, no):
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = session.get(DETAIL.format(no=no), headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200:
                d = r.json()
                return d.get("data", d)
            if r.status_code in (404, 410):
                return None                       # 판매 종료 등
            last = f"HTTP {r.status_code}"
        except Exception as e:                    # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        if attempt < RETRIES:
            time.sleep(SLEEP * (2 ** attempt))
    print(f"  !! {no} 실패 ({last})", flush=True)
    return "FAIL"


def main():
    csv = sorted(glob.glob(os.path.join(BASE, "kurly_kidswear_*.csv")))[-1]
    ts = re.search(r"(\d{8}_\d{6})", os.path.basename(csv)).group(1)
    df = pd.read_csv(csv)

    out = os.path.join(BASE, f"review_counts_{ts}.jsonl")
    done = set()
    if os.path.exists(out):
        for line in open(out, encoding="utf-8"):
            try:
                done.add(json.loads(line)["no"])
            except Exception:                     # noqa: BLE001
                pass

    targets = [int(n) for n in df.loc[df["리뷰수"] == 0, "상품ID"] if int(n) not in done]
    print(f"대상 {len(targets):,}건 (완료 {len(done):,}건) — 예상 {len(targets)*SLEEP/60:.0f}분",
          flush=True)

    session = requests.Session()
    fixed = 0
    with open(out, "a", encoding="utf-8") as f:
        for i, no in enumerate(targets, start=1):
            d = fetch(session, no)
            if d == "FAIL":
                rec = {"no": no, "review_count": None, "status": "fail"}
            elif d is None:
                rec = {"no": no, "review_count": None, "status": "gone"}
            else:
                rc = pd.to_numeric(d.get("review_count"), errors="coerce")
                rc = int(rc) if pd.notna(rc) else None
                rec = {"no": no, "review_count": rc, "status": "ok"}
                if rc:
                    fixed += 1
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if i % 100 == 0:
                print(f"  {i:,}/{len(targets):,}  보정발견 {fixed:,}건", flush=True)
            time.sleep(SLEEP)

    print(f"\n완료. 목록이 0 이었으나 실제 리뷰가 있던 상품: {fixed:,}건")
    print(f"저장: {os.path.basename(out)}")


if __name__ == "__main__":
    sys.exit(main())
