"""무신사 상품 랭킹(인기순) · 리뷰 수집기 — 학습/포트폴리오용 스켈레톤.

사용 예:
    # 아우터(002) 카테고리 인기순 상품 1페이지(40개) 수집
    python musinsa_crawler.py products --category 002 --pages 1

    # 특정 상품의 리뷰 50건 수집
    python musinsa_crawler.py reviews --goods-no 3082392 --max-reviews 50

    # products 결과 파일에 담긴 모든 상품의 리뷰를 상품당 30건씩 수집
    python musinsa_crawler.py reviews --from-products data/products_20260708.json --per-product 30

주의:
- 내부 API 엔드포인트는 사이트 개편 시 예고 없이 바뀝니다. 응답이 비거나 구조가
  다르면 README의 "엔드포인트 확인 방법"을 따라 브라우저 개발자도구에서 최신
  주소/파라미터를 확인해 아래 상수를 갱신하세요.
- 요청 간 딜레이를 지키고, 필요한 만큼만 소량 수집하세요. 수집 원본을 공개
  저장소에 올리지 마세요(자세한 내용은 README 참고).
"""

import argparse
import csv
import json
import random
import sys
import time
from datetime import date
from pathlib import Path

import requests

# Windows 콘솔(cp949)에서 한글 로그가 깨지지 않도록 출력을 UTF-8로 고정
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 설정 — 엔드포인트가 바뀌면 여기만 고치면 됩니다.
# ---------------------------------------------------------------------------

# 카테고리 상품 목록(PLP) API. 인기순 정렬이 사실상 카테고리 랭킹입니다.
PRODUCTS_API = "https://api.musinsa.com/api2/dp/v1/plp/goods"

# 상품 상세 페이지 하단 리뷰 목록 API.
REVIEWS_API = "https://goods.musinsa.com/api2/review/v1/view/list"

# 무신사 카테고리 코드 예시 (전체 목록은 사이트 카테고리 URL에서 확인 가능:
# https://www.musinsa.com/category/002 처럼 주소에 코드가 그대로 노출됨)
CATEGORY_NAMES = {
    "001": "상의",
    "002": "아우터",
    "003": "바지",
    "004": "가방",
    "005": "신발",
    "020": "원피스/스커트",
    "026": "속옷/홈웨어",
    
}

HEADERS = {
    # 실제 브라우저 UA를 쓰되, 문의 연락처를 남겨 수집 주체를 밝힙니다.
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 "
        "(personal-portfolio-crawler; contact: teamprism@teamprism.cloud)"
    ),
    "Accept": "application/json",
    "Referer": "https://www.musinsa.com/",
}

DELAY_RANGE = (1.5, 3.0)  # 요청 간 대기 시간(초) — 줄이지 마세요.
MAX_RETRIES = 3
CHANNEL = "무신사"

OUT_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# 공통 유틸
# ---------------------------------------------------------------------------

def polite_sleep():
    time.sleep(random.uniform(*DELAY_RANGE))


def get_json(session: requests.Session, url: str, params: dict) -> dict:
    """재시도 + 지수 백오프를 붙인 GET. 실패 시 빈 dict 반환."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            print(f"  ! HTTP {resp.status_code} ({url})", file=sys.stderr)
            if resp.status_code in (403, 429):
                # 차단/속도제한 신호 — 더 길게 쉬어야 함
                time.sleep(10 * attempt)
        except (requests.RequestException, ValueError) as e:
            print(f"  ! 요청 실패({attempt}/{MAX_RETRIES}): {e}", file=sys.stderr)
        time.sleep(2**attempt)
    return {}


def normalize_rating(value) -> str:
    """평점을 5점 만점 문자열로 환산. PLP API는 100점 만점(예: 96)으로 내려옴."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if v > 5:
        v /= 20
    return f"{round(v, 1):g}"


def first_of(d: dict, *keys, default=""):
    """응답 스키마 변동에 대비해 후보 키를 순서대로 조회."""
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def save_outputs(rows: list[dict], stem: str, dump_raw=None):
    OUT_DIR.mkdir(exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    json_path = OUT_DIR / f"{stem}_{stamp}.json"
    csv_path = OUT_DIR / f"{stem}_{stamp}.csv"

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    if dump_raw is not None:
        raw_path = OUT_DIR / f"{stem}_{stamp}_raw.json"
        raw_path.write_text(json.dumps(dump_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  원본 응답 저장: {raw_path} (파싱이 어긋나면 이 파일로 키 이름을 확인)")

    print(f"저장 완료: {json_path} / {csv_path} ({len(rows)}건)")


# ---------------------------------------------------------------------------
# 1) 상품 목록 (카테고리 인기순 = 랭킹)
# ---------------------------------------------------------------------------

def fetch_products(category: str, pages: int, size: int, dump_raw: bool) -> None:
    session = requests.Session()
    session.headers.update(HEADERS)

    category_name = CATEGORY_NAMES.get(category, category)
    today = date.today().isoformat()
    rows: list[dict] = []
    raw_pages: list[dict] = []

    for page in range(1, pages + 1):
        print(f"[{category_name}] {page}/{pages} 페이지 수집 중...")
        params = {
            "gf": "A",              # A=전체, M=남성, F=여성
            "category": category,
            "sortCode": "POPULAR",  # 인기순
            "page": page,
            "size": size,
            "caller": "CATEGORY",
        }
        payload = get_json(session, PRODUCTS_API, params)
        raw_pages.append(payload)

        # 응답 내 상품 배열 위치는 개편에 따라 다를 수 있어 후보 경로를 순회
        data = payload.get("data", payload)
        items = (
            first_of(data, "list", "goodsList", "items", default=None)
            or first_of(data.get("pagination", {}), "list", default=None)
            or []
        )
        if not items:
            print("  ! 상품 목록을 찾지 못했습니다. --dump-raw로 원본을 저장해 "
                  "README의 엔드포인트 확인 방법을 참고하세요.", file=sys.stderr)
            break

        for idx, item in enumerate(items, start=(page - 1) * size + 1):
            normal_price = first_of(item, "normalPrice", "originPrice", default=0)
            sale_price = first_of(item, "price", "salePrice", default=0)
            rows.append({
                "Channel": CHANNEL,
                "Category": category_name,
                "Rank": str(idx),
                "Product Name": first_of(item, "goodsName", "name"),
                "Brand": first_of(item, "brandName", "brand"),
                "Price": f"{int(sale_price):,}" if sale_price else "",
                "Original Price": f"{int(normal_price):,}" if normal_price else "",
                "Discount Rate": (
                    f"{first_of(item, 'saleRate', 'discountRate', default=0)}%"
                ),
                "Review Count": f"{int(first_of(item, 'reviewCount', default=0)):,}",
                "Rating": normalize_rating(first_of(item, "reviewScore", "rating", default="")),
                "Collected Date": today,
                # 리뷰 수집 단계에서 사용하는 내부 키 (포트폴리오 산출물에선 제거 가능)
                "_goods_no": str(first_of(item, "goodsNo", "goodsNumber", "id")),
            })
        polite_sleep()

    save_outputs(rows, f"products_{category}", raw_pages if dump_raw else None)


# ---------------------------------------------------------------------------
# 2) 리뷰
# ---------------------------------------------------------------------------

def fetch_reviews_for_goods(session: requests.Session, goods_no: str,
                            product_name: str, max_reviews: int) -> list[dict]:
    rows: list[dict] = []
    page = 0
    page_size = 20

    while len(rows) < max_reviews:
        params = {
            "page": page,
            "pageSize": page_size,
            "goodsNo": goods_no,
            "sort": "up_cnt_desc",  # 도움돼요 순. 최신순은 new
            "selectedSimilarNo": goods_no,
            "myFilter": "false",
            "hasPhoto": "false",
            "isExperience": "false",
        }
        payload = get_json(session, REVIEWS_API, params)
        data = payload.get("data", payload)
        reviews = first_of(data, "list", "reviews", "items", default=None) or []
        if not reviews:
            break

        for r in reviews:
            profile = r.get("userProfileInfo") or {}
            height = first_of(profile, "userHeight", "reviewerHeight", "height")
            weight = first_of(profile, "userWeight", "reviewerWeight", "weight")
            option = first_of(r, "goodsOption", "option")
            reviewer_bits = [b for b in (
                f"{height}cm" if height else "",
                f"{weight}kg" if weight else "",
                f"{option} 구매" if option else "",
            ) if b]

            rows.append({
                "Channel": CHANNEL,
                "Product Name": product_name or first_of(r.get("goods", {}), "goodsName"),
                "Rating": str(first_of(r, "grade", "rating", "score")),
                "Review Body": str(first_of(r, "content", "reviewContent")).strip(),
                "Review Date": str(first_of(r, "createDate", "createdAt"))[:10],
                "Reviewer Info": " / ".join(reviewer_bits),
            })
            if len(rows) >= max_reviews:
                break

        page += 1
        polite_sleep()

    return rows


def fetch_reviews(args) -> None:
    session = requests.Session()
    session.headers.update(HEADERS)

    # 대상 상품 목록 구성: 단일 goods-no 또는 products 결과 파일
    # stem에 출처를 넣어 카테고리별 수집 파일이 서로 덮어쓰지 않게 함
    targets: list[tuple[str, str]] = []  # (goods_no, product_name)
    if args.goods_no:
        targets.append((args.goods_no, args.product_name or ""))
        stem = f"reviews_{args.goods_no}"
    elif args.from_products:
        products = json.loads(Path(args.from_products).read_text(encoding="utf-8"))
        targets = [(p["_goods_no"], p["Product Name"]) for p in products if p.get("_goods_no")]
        # products_026_20260708 → reviews_026
        stem = "reviews_" + Path(args.from_products).stem.replace("products_", "").rsplit("_", 1)[0]
    else:
        print("--goods-no 또는 --from-products 중 하나를 지정하세요.", file=sys.stderr)
        sys.exit(1)

    per_product = args.per_product or args.max_reviews
    all_rows: list[dict] = []
    for i, (goods_no, name) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] 리뷰 수집: {name or goods_no}")
        all_rows.extend(fetch_reviews_for_goods(session, goods_no, name, per_product))

    save_outputs(all_rows, stem)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="무신사 상품/리뷰 수집기 (학습용)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("products", help="카테고리 인기순 상품 목록 수집")
    p.add_argument("--category", default="002", help="카테고리 코드 (기본: 002 아우터)")
    p.add_argument("--pages", type=int, default=1, help="수집할 페이지 수")
    p.add_argument("--size", type=int, default=40, help="페이지당 상품 수")
    p.add_argument("--dump-raw", action="store_true", help="API 원본 응답도 저장")

    r = sub.add_parser("reviews", help="상품 리뷰 수집")
    r.add_argument("--goods-no", help="상품 번호 (상품 URL의 /products/ 뒤 숫자)")
    r.add_argument("--product-name", help="상품명 (출력에 기록용, 선택)")
    r.add_argument("--from-products", help="products 명령이 만든 JSON 파일 경로")
    r.add_argument("--max-reviews", type=int, default=50, help="단일 상품 최대 리뷰 수")
    r.add_argument("--per-product", type=int, help="--from-products 사용 시 상품당 리뷰 수")

    args = parser.parse_args()
    if args.command == "products":
        fetch_products(args.category, args.pages, args.size, args.dump_raw)
    else:
        fetch_reviews(args)


if __name__ == "__main__":
    main()
