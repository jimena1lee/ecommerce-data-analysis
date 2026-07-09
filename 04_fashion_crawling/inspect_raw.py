"""--dump-raw로 저장한 원본 JSON의 구조 요약 — 파싱이 깨졌을 때 진단용.

사용:
    python inspect_raw.py data/kurly_products_165_20260709_raw.json

출력:
    1) 트리에 존재하는 모든 키 경로(배열 인덱스는 []로 압축)와 등장 횟수
    2) URL/API로 보이는 문자열 전체 목록

출력을 통째로 복사해 이슈/대화에 붙이면 어떤 키를 파싱해야 할지 알 수 있습니다.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAX_PATHS = 400
MAX_STRINGS = 60


def walk(node, path, paths: Counter, strings: set, examples: dict):
    if isinstance(node, dict):
        if not node:
            paths[f"{path} (빈 dict)"] += 1
        for k, v in node.items():
            walk(v, f"{path}.{k}", paths, strings, examples)
    elif isinstance(node, list):
        if not node:
            paths[f"{path}[] (빈 배열)"] += 1
        # 배열 요소는 앞쪽 3개만 대표로 순회 (구조 파악에는 충분)
        for x in node[:3]:
            walk(x, f"{path}[]", paths, strings, examples)
    else:
        paths[path] += 1
        if path not in examples:
            examples[path] = repr(node)[:60]
        if isinstance(node, str) and re.search(r"https?://|api\.|/v\d+/", node):
            strings.add(node[:200])


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    tree = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    paths: Counter = Counter()
    strings: set = set()
    examples: dict = {}
    walk(tree, "$", paths, strings, examples)

    print(f"== 키 경로 ({len(paths)}종) ==")
    for p, n in sorted(paths.items())[:MAX_PATHS]:
        ex = f"  예: {examples[p]}" if p in examples else ""
        print(f"  {p}  x{n}{ex}")
    if len(paths) > MAX_PATHS:
        print(f"  ... 외 {len(paths) - MAX_PATHS}종 생략")

    print(f"\n== URL/API로 보이는 문자열 ({len(strings)}개) ==")
    for s in sorted(strings)[:MAX_STRINGS]:
        print(f"  {s}")
    if len(strings) > MAX_STRINGS:
        print(f"  ... 외 {len(strings) - MAX_STRINGS}개 생략")


if __name__ == "__main__":
    main()
