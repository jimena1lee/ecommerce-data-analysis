#!/usr/bin/env python3
"""portfolio/index.html을 제출용 PDF(A4)로 만든다.

인쇄본은 화면본과 두 가지가 다르다.
  1. iframe 데모는 인쇄에서 잘리므로, headless Chrome으로 전체 높이를 캡처한 뒤
     A4 한 장에 들어가는 조각으로 나눠 이미지로 싣는다.
  2. 버튼을 눌러야 결과가 보이는 데모(매크로·챗봇)는 캡처 전에 클릭을 재현한다.

Chromium이 필요하다(PLAYWRIGHT_BROWSERS_PATH 아래 번들 사용).
"""
import base64
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_portfolio_single_file import PAGES, VIDEO_STILL, data_uri  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "portfolio" / "index.html"
OUT = ROOT / "dist" / "이지원-이커머스MD-포트폴리오.pdf"

CHROME_CANDIDATES = [
    Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome"),
    Path(shutil.which("chromium") or "/nonexistent"),
    Path(shutil.which("google-chrome") or "/nonexistent"),
]

SHOT_W = 1000          # 데모 캡처 폭(px) — 데스크톱 레이아웃 유지
SLICE_H = 1380         # A4 한 장에 들어가는 조각 높이(px). 190mm 폭 기준 273mm 이내.

# 캡처할 데모. act = 캡처 전에 실행할 클릭 재현 스크립트.
DEMOS = [
    dict(ref="../04_fashion_crawling/kurly/output/dashboard_generic.html", act=None),
    dict(ref="../portfolio-oliveyoung/logistics-calculator.html", act=None),
    dict(ref="../portfolio-oliveyoung/report-macro-flow.html",
         act="document.getElementById('run').click();"),
    # SNS 피드 썸네일은 외부(구글 드라이브) 이미지라 캡처하면 빈 칸으로 남는다.
    dict(ref="../04_fashion_crawling/instagram-feed-v5.html", note=(
        "게시물 썸네일을 외부에서 불러오는 피드라 인쇄본에는 담지 못했습니다. "
        "아래 주소에서 실제 콘텐츠를 보실 수 있습니다.")),
    dict(ref="../04_fashion_crawling/runningshoes-gpt.html",
         act="document.querySelector('#examples button')?.click();"),
]

PRINT_CSS = """
@page { size:A4; margin:12mm 10mm; }
@media print {
  nav, .scroll-hint { display:none !important; }
  .reveal { opacity:1 !important; transform:none !important; }
  html, body { background:#fff !important; }
  #hero { min-height:auto !important; padding:8px 0 24px !important;
          background:none !important; break-after:page; }
  #hero h1 { font-size:2.1rem !important; }
  section { padding-top:22px !important; }
  h2 { font-size:1.5rem !important; }
  h2, h3, h4 { break-after:avoid; }
  p, li { orphans:2; widows:2; }
  figure.evidence, .evidence-grid, .exclusive-card, table { break-inside:avoid; }
  /* 조각 단위로만 페이지를 넘긴다 — 데모 전체를 묶으면 A4를 넘겨 잘린다. */
  .demo-shot { margin:16px 0; break-inside:auto; }
  .shot-slice { break-inside:avoid; }
  .embed .open::after, .demo-shot .open::after { content:" — " attr(href); word-break:break-all; }
  a { text-decoration:none; }
  .print-only { display:block !important; }
}
.print-only { display:none; }
/* 데모 캡처 조각 — 컨테이너 폭을 기준으로 배율이 정해지므로 % 오프셋을 쓴다. */
.shot-slice { overflow:hidden; border:1px solid var(--line); background:#fff;
              box-shadow:var(--card-shadow); }
.shot-slice.first { border-radius:14px 14px 0 0; }
.shot-slice.last { border-radius:0 0 14px 14px; }
.shot-slice.only { border-radius:14px; }
.shot-slice img { width:100%; display:block; }
.demo-note { border:1px solid var(--line); border-radius:14px; background:var(--accent-tint);
             padding:16px 18px; color:var(--sub); font-size:.92rem; }
"""


def chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c.exists():
            return str(c)
    sys.exit("Chromium을 찾지 못했습니다.")


def run_chrome(*args: str) -> str:
    proc = subprocess.run(
        [chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         *args],
        capture_output=True, text=True, timeout=180,
    )
    return proc.stdout


MEASURE_JS = """
<script>addEventListener('load',()=>{setTimeout(()=>{try{%s}catch(e){}setTimeout(()=>{
  let b=0;
  for (const el of document.querySelectorAll('body *')) {
    const s=getComputedStyle(el);
    if (s.position==='fixed'||s.display==='none'||s.visibility==='hidden') continue;
    b=Math.max(b, el.getBoundingClientRect().bottom+window.scrollY);
  }
  b=Math.min(Math.ceil(b)+24, document.documentElement.scrollHeight);
  document.title='H='+b;
},%d)},400)})</script>
"""


def capture(demo: dict, work: Path) -> tuple[Path, int]:
    """데모를 전체 높이로 캡처해 (png 경로, 높이)를 돌려준다."""
    name = Path(demo["ref"]).stem
    page = (SRC.parent / demo["ref"]).resolve()
    settle = 2500 if demo.get("act") else 1200
    probe = work / f"{name}.html"
    probe.write_text(
        page.read_text(encoding="utf-8") + MEASURE_JS % (demo.get("act") or "", settle),
        encoding="utf-8",
    )
    dom = run_chrome("--virtual-time-budget=15000", f"--window-size={SHOT_W},900",
                     "--dump-dom", f"file://{probe}")
    m = re.search(r"H=(\d+)", dom)
    if not m:
        sys.exit(f"{name}: 높이 측정 실패")
    height = int(m.group(1))
    png = work / f"{name}.png"
    run_chrome("--virtual-time-budget=15000", f"--window-size={SHOT_W},{height}",
               f"--screenshot={png}", f"file://{probe}")
    if not png.exists():
        sys.exit(f"{name}: 캡처 실패")
    return png, height


def slices_html(png: Path, height: int) -> str:
    """캡처를 A4 한 장에 들어가는 조각으로 나눈 마크업."""
    uri = data_uri(png)
    n = max(1, -(-height // SLICE_H))
    out = []
    for i in range(n):
        top = i * SLICE_H
        h = min(SLICE_H, height - top)
        pos = "only" if n == 1 else "first" if i == 0 else "last" if i == n - 1 else ""
        out.append(
            f'<div class="shot-slice {pos}" style="aspect-ratio:{SHOT_W}/{h}">'
            f'<img src="{uri}" alt="" style="margin-top:{-top / SHOT_W:.4%}"></div>'
        )
    return "".join(out)


def main() -> None:
    doc = SRC.read_text(encoding="utf-8")
    work = Path(tempfile.mkdtemp(prefix="portfolio-pdf-"))

    # 1. 로컬 이미지 내장
    doc = re.sub(r'src="(assets/[^"]+)"',
                 lambda m: f'src="{data_uri((SRC.parent / m.group(1)).resolve())}"', doc)

    # 2. iframe → 캡처 이미지(또는 안내문)
    for demo in DEMOS:
        ref = demo["ref"]
        pattern = re.compile(r'<iframe src="' + re.escape(ref) + r'"[^>]*></iframe>')
        if not pattern.search(doc):
            sys.exit(f"iframe을 찾지 못했습니다: {ref}")
        if demo.get("note"):
            body = f'<div class="demo-note">{demo["note"]}</div>'
            print(f"  · {Path(ref).stem}: 안내문으로 대체")
        else:
            png, height = capture(demo, work)
            body = slices_html(png, height)
            print(f"  · {Path(ref).stem}: {SHOT_W}×{height}px 캡처")
        doc = pattern.sub(lambda _m, b=body: f'<div class="demo-shot">{b}</div>', doc, count=1)

    # 3. 영상 → 애니메이션 WebP의 첫 프레임
    doc = re.sub(
        r'<video class="reveal" src="\.\./[^"]+"[^>]*></video>',
        f'<img class="reveal video-still" src="{data_uri(VIDEO_STILL)}"'
        ' alt="AI로 역동성을 부여한 브랜드 광고 콘텐츠">'
        '<p class="print-only" style="text-align:center;font-size:.85rem;color:var(--sub)">'
        f'영상 콘텐츠입니다 — 재생은 웹 버전에서 확인하실 수 있습니다: {PAGES}portfolio/</p>',
        doc,
    )
    doc = doc.replace("  video { width:100%;", "  video, .video-still { width:100%;")

    # 4. 남은 로컬 경로 → 공개 URL, 인쇄용 CSS 주입
    doc = re.sub(r'(href|src)="\.\./([^"]+)"', rf'\1="{PAGES}\2"', doc)
    doc = doc.replace("</style>", PRINT_CSS + "</style>", 1)
    doc = doc.replace(
        "</header>",
        '<p class="print-only" style="margin-top:18px;font-size:.9rem;color:var(--sub)">'
        f'인터랙티브 웹 버전 · {PAGES}portfolio/</p></header>', 1)

    print_html = work / "print.html"
    print_html.write_text(doc, encoding="utf-8")
    OUT.parent.mkdir(exist_ok=True)
    run_chrome("--virtual-time-budget=20000", "--window-size=1000,1400",
               "--no-pdf-header-footer", f"--print-to-pdf={OUT}", f"file://{print_html}")
    if not OUT.exists():
        sys.exit("PDF 생성 실패")
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"   중간 산출물: {work}")


if __name__ == "__main__":
    main()
