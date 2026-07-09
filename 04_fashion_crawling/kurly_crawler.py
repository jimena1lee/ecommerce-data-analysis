"""컬리(Kurly) 패션 카테고리 상품 · 리뷰 수집기 — 학습/포트폴리오용 스켈레톤.

무신사 수집기(musinsa_crawler.py)와 같은 구조/출력 스키마를 씁니다.

사용 예:
    # 패션 카테고리(165) 상품 1페이지(96개) 수집
    python kurly_crawler.py products --category 165 --pages 1

    # 특정 상품의 리뷰 50건 수집 (상품 URL: kurly.com/goods/1000123456)
    python kurly_crawler.py reviews --product-no 1000123456 --max-reviews 50

    # products 결과 파일에 담긴 모든 상품의 리뷰를 상품당 30건씩 수집
    python kurly_crawler.py reviews --from-products data/kurly_products_165_20260709.json --per-product 30

주의:
- 컬리 API는 요청에 Authorization: Bearer 토큰을 요구할 수 있습니다.
  401/403이 나오면 브라우저 개발자도구에서 토큰을 복사해
  환경변수 KURLY_TOKEN 또는 --token 옵션으로 넘기세요(README 참고).
- 내부 API 엔드포인트는 사이트 개편 시 예고 없이 바뀝니다. 응답이 비거나 구조가
  다르면 README의 "엔드포인트 확인 방법"을 따라 최신 주소/파라미터를 확인해
  아래 상수를 갱신하세요.
- 요청 간 딜레이를 지키고, 필요한 만큼만 소량 수집하세요. 수집 원본을 공개
  저장소에 올리지 마세요(자세한 내용은 README 참고).
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests

# Windows 콘솔(cp949)에서 한글 로그가 깨지지 않도록 출력을 UTF-8로 고정
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 설정 — 엔드포인트가 바뀌면 여기만 고치면 됩니다.
# ---------------------------------------------------------------------------

# 카테고리 상품 목록(PLP) API. {category_no} 자리에 카테고리 코드가 들어갑니다.
# (2026-07 개발자도구로 확인한 실제 주소)
PRODUCTS_API = ("https://api.kurly.com/collection/v2/home/sites/market/"
                "product-categories/{category_no}/products")

# API가 404 등으로 실패하면 카테고리 페이지 HTML의 __NEXT_DATA__(서버렌더링
# 데이터)에서 상품을 직접 추출합니다. 이때 페이지가 실제로 쓰는 API 주소
# 힌트도 함께 출력하므로, 위 상수를 올바른 값으로 갱신할 수 있습니다.
CATEGORY_PAGE = "https://www.kurly.com/categories/{category_no}"

# 상품 상세 페이지 하단 리뷰 목록 API. 커서(after) 기반 페이지네이션.
REVIEWS_API = "https://api.kurly.com/product-review/v1/contents-products/{product_no}/reviews"

# 컬리 카테고리 코드 예시 (전체 목록은 사이트 카테고리 URL에서 확인 가능:
# https://www.kurly.com/categories/165 처럼 주소에 코드가 그대로 노출됨)
# 이름이 비어 있으면 "카테고리 <코드>"로 표기됩니다 — 페이지 상단 타이틀을 보고 채우세요.
CATEGORY_NAMES = {
    "165": "",
    "166": "",
    "169": "",
}

HEADERS = {
    # 실제 브라우저 UA를 쓰되, 문의 연락처를 남겨 수집 주체를 밝힙니다.
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 "
        "(personal-portfolio-crawler; contact: teamprism@teamprism.cloud)"
    ),
    "Accept": "application/json",
    "Referer": "https://www.kurly.com/",
    "Origin": "https://www.kurly.com",
}

DELAY_RANGE = (1.5, 3.0)  # 요청 간 대기 시간(초) — 줄이지 마세요.
MAX_RETRIES = 3
CHANNEL = "컬리"

OUT_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# 공통 유틸 (musinsa_crawler.py와 동일 패턴)
# ---------------------------------------------------------------------------

def polite_sleep():
    time.sleep(random.uniform(*DELAY_RANGE))


def make_session(token: str | None) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    token = token or os.environ.get("KURLY_TOKEN", "")
    if token:
        # 개발자도구에서 복사한 값이 "Bearer xxx" 형태여도 그대로 동작하게 처리
        if not token.lower().startswith("bearer "):
            token = f"Bearer {token}"
        session.headers["Authorization"] = token
    return session


def get_json(session: requests.Session, url: str, params: dict) -> dict:
    """재시도 + 지수 백오프를 붙인 GET. 실패 시 빈 dict 반환."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            print(f"  ! HTTP {resp.status_code} ({url})", file=sys.stderr)
            if resp.status_code == 404:
                # 엔드포인트가 바뀐 것 — 재시도해도 소용없으니 바로 반환
                return {}
            if resp.status_code in (401,):
                print("  ! 인증 실패 — 개발자도구에서 Bearer 토큰을 복사해 "
                      "KURLY_TOKEN 환경변수 또는 --token으로 넘기세요(README 참고).",
                      file=sys.stderr)
                return {}
            if resp.status_code in (403, 429):
                # 차단/속도제한 신호 — 더 길게 쉬어야 함
                time.sleep(10 * attempt)
        except (requests.RequestException, ValueError) as e:
            print(f"  ! 요청 실패({attempt}/{MAX_RETRIES}): {e}", file=sys.stderr)
        time.sleep(2**attempt)
    return {}


def first_of(d: dict, *keys, default=""):
    """응답 스키마 변동에 대비해 후보 키를 순서대로 조회."""
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def extract_brand(name: str) -> str:
    """컬리는 목록 API에 브랜드 필드가 따로 없고 상품명이 '[브랜드] 상품명' 형태."""
    m = re.match(r"^\s*\[([^\]]+)\]", name or "")
    return m.group(1).strip() if m else ""


def to_date_str(value) -> str:
    """등록일이 epoch(ms) 숫자로 오거나 ISO 문자열로 오는 경우 모두 YYYY-MM-DD로."""
    if isinstance(value, (int, float)) and value > 0:
        if value > 1e12:  # 밀리초
            value /= 1000
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d")
    return str(value)[:10]


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
# 1) 상품 목록 (카테고리)
# ---------------------------------------------------------------------------

def iter_nodes(node):
    """중첩 dict/list를 전부 순회 (HTML 폴백에서 상품 배열 탐색용)."""
    yield node
    if isinstance(node, dict):
        for v in node.values():
            yield from iter_nodes(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_nodes(v)


def looks_like_product(d) -> bool:
    return (
        isinstance(d, dict)
        and bool(first_of(d, "name", "goodsName", "productName"))
        and any(k in d for k in ("sales_price", "discounted_price", "review_count",
                                 "salesPrice", "discountedPrice", "no", "productNo"))
    )


def find_product_list(tree) -> list:
    """__NEXT_DATA__ 트리에서 상품 dict로만 이뤄진 가장 긴 배열을 찾는다."""
    best: list = []
    for node in iter_nodes(tree):
        if (isinstance(node, list) and node
                and all(looks_like_product(x) for x in node)
                and len(node) > len(best)):
            best = node
    return best


def print_api_hints(tree):
    """페이지가 실제로 쓰는 API 주소/쿼리키를 출력 — 상단 상수 갱신용 힌트."""
    hints: set[str] = set()
    for node in iter_nodes(tree):
        if isinstance(node, str) and "api.kurly.com" in node:
            hints.add(node)
        elif isinstance(node, dict) and node.get("queryKey"):
            hints.add(json.dumps(node["queryKey"], ensure_ascii=False)[:150])
    if hints:
        print("  ↳ 페이지에서 발견한 API 힌트 (PRODUCTS_API/REVIEWS_API 갱신에 사용):")
        for h in sorted(hints)[:12]:
            print(f"      {h}")


def category_name_from_next_data(tree) -> str:
    """__NEXT_DATA__의 categoryData.name (2026-07 구조 확인)."""
    cat = tree.get("props", {}).get("pageProps", {}).get("categoryData", {}) or {}
    return str(cat.get("name") or "")


def category_name_from_html(html: str) -> str:
    m = re.search(r"<title>([^<]+)</title>", html)
    if not m:
        return ""
    t = re.split(r"[|\-–]", m.group(1))[0].strip()
    return "" if t.lower() in ("kurly", "마켓컬리", "컬리", "뷰티컬리") else t


def fetch_products_page_html(session: requests.Session, category: str, page: int,
                             size: int, sort_type: str) -> tuple[list, dict, str]:
    """카테고리 페이지 HTML의 __NEXT_DATA__에서 상품 추출. (items, raw, 카테고리명)"""
    url = CATEGORY_PAGE.format(category_no=category)
    params = {"page": page, "per_page": size, "sorted_type": sort_type}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=15,
                               headers={"Accept": "text/html,application/xhtml+xml"})
            if resp.status_code == 200:
                m = re.search(
                    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                    resp.text, re.S)
                if not m:
                    print("  ! __NEXT_DATA__를 찾지 못했습니다(봇 차단 페이지일 수 있음).",
                          file=sys.stderr)
                    return [], {}, ""
                tree = json.loads(m.group(1))
                name = category_name_from_next_data(tree) or category_name_from_html(resp.text)
                return find_product_list(tree), tree, name
            print(f"  ! HTTP {resp.status_code} ({url})", file=sys.stderr)
            if resp.status_code in (403, 429):
                time.sleep(10 * attempt)
        except (requests.RequestException, ValueError) as e:
            print(f"  ! 요청 실패({attempt}/{MAX_RETRIES}): {e}", file=sys.stderr)
        time.sleep(2**attempt)
    return [], {}, ""


def fetch_products(args) -> None:
    session = make_session(args.token)

    category = args.category
    category_name = CATEGORY_NAMES.get(category) or f"카테고리 {category}"
    today = date.today().isoformat()
    rows: list[dict] = []
    raw_pages: list[dict] = []
    use_html = False  # API 실패 시 HTML 폴백으로 전환

    for page in range(1, args.pages + 1):
        print(f"[{category_name}] {page}/{args.pages} 페이지 수집 중...")
        items: list = []

        if not use_html:
            params = {
                "page": page,
                "per_page": args.size,
                # 정렬 코드는 개편에 따라 다를 수 있음 — 개발자도구에서 정렬 탭을
                # 바꿔가며 sort_type 값을 확인하세요(기본값은 사이트 기본 정렬).
                "sort_type": args.sort_type,
                "filters": "",
            }
            payload = get_json(session, PRODUCTS_API.format(category_no=category), params)
            raw_pages.append(payload)
            data = payload.get("data", payload)
            # 이 API는 상품 배열이 data 바로 아래에 리스트로 내려옴 (2026-07 확인)
            if isinstance(data, list):
                items = data
            else:
                items = first_of(data, "products", "list", "items", default=None) or []
            if not items and page == 1:
                print("  ! API 수집 실패 — 카테고리 페이지 HTML(__NEXT_DATA__)로 "
                      "대체 수집합니다.")
                use_html = True

        if use_html:
            items, tree, html_name = fetch_products_page_html(
                session, category, page, args.size, args.sort_type)
            raw_pages.append(tree)
            if page == 1:
                print_api_hints(tree)
                if html_name and not CATEGORY_NAMES.get(category):
                    category_name = html_name
                    print(f"  ↳ 카테고리명 자동 인식: {category_name}")

        if not items:
            print("  ! 상품 목록을 찾지 못했습니다. --dump-raw로 원본을 저장해 "
                  "README의 엔드포인트 확인 방법을 참고하세요.", file=sys.stderr)
            break

        for idx, item in enumerate(items, start=(page - 1) * args.size + 1):
            # 키 이름은 snake_case (2026-07 응답 기준). camelCase는 예비 후보.
            name = str(first_of(item, "name", "goodsName", "productName"))
            normal_price = first_of(item, "sales_price", "salesPrice", "price", default=0)
            sale_price = first_of(item, "discounted_price", "discountedPrice", default=0) or normal_price
            discount_rate = first_of(item, "discount_rate", "discountRate", "saleRate", default=0)
            # 리뷰 수가 "999+" 같은 문자열로 내려오는 경우가 있어 그대로 보존
            review_count = first_of(item, "review_count", "reviewCount", default="0")
            rows.append({
                "Channel": CHANNEL,
                "Category": category_name,
                "Rank": str(idx),
                "Product Name": name,
                "Brand": extract_brand(name),
                "Price": f"{int(sale_price):,}" if sale_price else "",
                "Original Price": f"{int(normal_price):,}" if normal_price else "",
                "Discount Rate": f"{discount_rate}%",
                "Review Count": str(review_count),
                # 컬리는 별점 제도가 없어 목록/리뷰 모두 Rating이 비어 있음
                "Rating": "",
                "Collected Date": today,
                # 리뷰 수집 단계에서 사용하는 내부 키 (포트폴리오 산출물에선 제거 가능)
                "_goods_no": str(first_of(item, "no", "productNo", "id")),
            })
        polite_sleep()

    save_outputs(rows, f"kurly_products_{category}", raw_pages if args.dump_raw else None)


# ---------------------------------------------------------------------------
# 2) 리뷰
# ---------------------------------------------------------------------------

def fetch_reviews_for_product(session: requests.Session, product_no: str,
                              product_name: str, max_reviews: int) -> list[dict]:
    rows: list[dict] = []
    after = ""  # 커서 기반 페이지네이션 — 응답 meta에서 다음 커서를 받아 이어감

    while len(rows) < max_reviews:
        params = {
            "sortType": "RECENTLY",  # 최신순. 추천순은 RECOMMEND
            "size": 10,
            "onlyImage": "false",
        }
        if after:
            params["after"] = after
        payload = get_json(session, REVIEWS_API.format(product_no=product_no), params)
        data = payload.get("data", payload)
        reviews = first_of(data, "list", "reviews", "contents", "items", default=None) or []
        if not reviews:
            break

        for r in reviews:
            option = first_of(r, "dealProductName", "optionName", "option")
            rows.append({
                "Channel": CHANNEL,
                "Product Name": product_name
                                or first_of(r, "contentsProductName", "productName"),
                "Rating": "",  # 컬리 후기에는 별점이 없음
                "Review Body": str(first_of(r, "contents", "content", "reviewContent")).strip(),
                "Review Date": to_date_str(first_of(r, "registeredAt", "createdAt", "registeredAtText")),
                "Reviewer Info": f"{option} 구매" if option else "",
            })
            if len(rows) >= max_reviews:
                break

        # 다음 페이지 커서 — 위치 후보를 순회하고, 없으면 종료
        meta = first_of(data, "meta", default={}) or {}
        pagination = first_of(meta, "pagination", default=meta) or {}
        after = str(first_of(pagination, "after", "nextCursor", default=""))
        if not after or not first_of(pagination, "hasNext", default=True):
            break
        polite_sleep()

    return rows


def fetch_reviews(args) -> None:
    session = make_session(args.token)

    # 대상 상품 목록 구성: 단일 product-no 또는 products 결과 파일
    # stem에 출처를 넣어 카테고리별 수집 파일이 서로 덮어쓰지 않게 함
    targets: list[tuple[str, str]] = []  # (product_no, product_name)
    if args.product_no:
        targets.append((args.product_no, args.product_name or ""))
        stem = f"kurly_reviews_{args.product_no}"
    elif args.from_products:
        products = json.loads(Path(args.from_products).read_text(encoding="utf-8"))
        targets = [(p["_goods_no"], p["Product Name"]) for p in products if p.get("_goods_no")]
        # kurly_products_165_20260709 → kurly_reviews_165
        stem = "kurly_reviews_" + (
            Path(args.from_products).stem.replace("kurly_products_", "").rsplit("_", 1)[0]
        )
    else:
        print("--product-no 또는 --from-products 중 하나를 지정하세요.", file=sys.stderr)
        sys.exit(1)

    per_product = args.per_product or args.max_reviews
    all_rows: list[dict] = []
    for i, (product_no, name) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] 리뷰 수집: {name or product_no}")
        all_rows.extend(fetch_reviews_for_product(session, product_no, name, per_product))
        polite_sleep()

    if not all_rows:
        print("  ! 후기를 하나도 수집하지 못했습니다. 상품 상세 페이지의 후기 영역을 "
              "연 상태로 개발자도구 Network 탭에서 실제 리뷰 API 주소를 확인해 "
              "REVIEWS_API 상수를 갱신하세요. products 명령의 HTML 폴백이 출력하는 "
              "API 힌트도 참고가 됩니다.", file=sys.stderr)

    save_outputs(all_rows, stem)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="컬리 상품/리뷰 수집기 (학습용)")
    parser.add_argument("--token", help="Authorization Bearer 토큰 (기본: 환경변수 KURLY_TOKEN)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("products", help="카테고리 상품 목록 수집")
    p.add_argument("--category", default="165", help="카테고리 코드 (기본: 165)")
    p.add_argument("--pages", type=int, default=1, help="수집할 페이지 수")
    p.add_argument("--size", type=int, default=96, help="페이지당 상품 수")
    p.add_argument("--sort-type", default="4", help="정렬 코드 (개발자도구에서 확인)")
    p.add_argument("--dump-raw", action="store_true", help="API 원본 응답도 저장")

    r = sub.add_parser("reviews", help="상품 리뷰 수집")
    r.add_argument("--product-no", help="상품 번호 (상품 URL의 /goods/ 뒤 숫자)")
    r.add_argument("--product-name", help="상품명 (출력에 기록용, 선택)")
    r.add_argument("--from-products", help="products 명령이 만든 JSON 파일 경로")
    r.add_argument("--max-reviews", type=int, default=50, help="단일 상품 최대 리뷰 수")
    r.add_argument("--per-product", type=int, help="--from-products 사용 시 상품당 리뷰 수")

    args = parser.parse_args()
    if args.command == "products":
        fetch_products(args)
    else:
        fetch_reviews(args)


if __name__ == "__main__":
    main()
