#!/usr/bin/env python3
"""portfolio/index.html을 제출용 단일 HTML 파일로 묶는다.

- assets/ 이미지 → base64 data URI로 내장
- iframe(로컬 HTML 5개) → srcdoc으로 본문 내장 (오프라인에서도 동작)
- brand-video.mp4(10MB) → 같은 영상의 애니메이션 WebP(640w)로 대체
- 로컬 경로 링크(../...) → GitHub Pages 절대 URL로 교체
"""
import base64
import html
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "portfolio" / "index.html"
OUT = ROOT / "dist" / "이지원-이커머스MD-포트폴리오.html"
PAGES = "https://jimena1lee.github.io/ecommerce-data-analysis/"
VIDEO_STILL = ROOT / "04_fashion_crawling" / "brand-video-640w.webp"


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def resolve(ref: str) -> Path:
    return (SRC.parent / ref).resolve()


def main() -> None:
    doc = SRC.read_text(encoding="utf-8")

    # ── 1. 로컬 이미지 내장 ────────────────────────────────
    def inline_img(m: re.Match) -> str:
        path = resolve(m.group(1))
        return f'src="{data_uri(path)}"'

    doc, n_img = re.subn(r'src="(assets/[^"]+)"', inline_img, doc)

    # ── 2. iframe 본문을 srcdoc으로 내장 ───────────────────
    def inline_iframe(m: re.Match) -> str:
        ref, rest = m.group(1), m.group(2)
        inner = resolve(ref).read_text(encoding="utf-8")
        srcdoc = html.escape(inner, quote=True)
        return f'<iframe srcdoc="{srcdoc}"{rest}>'

    doc, n_frame = re.subn(r'<iframe src="(\.\./[^"]+)"([^>]*)>', inline_iframe, doc)

    # ── 3. 영상 → 애니메이션 WebP 스틸로 대체 ──────────────
    doc, n_video = re.subn(
        r'<video class="reveal" src="\.\./[^"]+"[^>]*></video>',
        f'<img class="reveal video-still" src="{data_uri(VIDEO_STILL)}"'
        ' alt="AI로 역동성을 부여한 브랜드 광고 콘텐츠" decoding="async">',
        doc,
    )
    doc = doc.replace(
        "  video { width:100%;",
        "  video, .video-still { width:100%;",
    )

    # ── 4. 남은 로컬 경로 링크 → 공개 URL ──────────────────
    doc, n_link = re.subn(r'(href|src)="\.\./([^"]+)"', rf'\1="{PAGES}\2"', doc)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(
        f"이미지 {n_img}개 · iframe {n_frame}개 · 영상 {n_video}개 내장, "
        f"남은 링크 {n_link}개 절대경로화\n"
        f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024 / 1024:.1f} MB)"
    )


if __name__ == "__main__":
    main()
