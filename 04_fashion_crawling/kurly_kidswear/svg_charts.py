# -*- coding: utf-8 -*-
"""대시보드 SVG 차트. 데이터 → SVG 문자열, 순수 함수만 둔다.

색은 CSS 변수로만 참조한다. SVG 안에 hex 를 쓰면 다크모드에서 대비가 깨진다.
"""
import html as _html

W = 760          # 뷰박스 기준 폭. .page 최대폭 860 - 좌우 패딩
INK = "var(--ink)"
MUTED = "var(--muted)"
LINE = "var(--hairline)"
DAWN = "var(--blue)"          # 샛별배송
SELLER = "var(--muted)"       # 판매자배송
ACCENT = "var(--kurly)"


def _esc(s):
    return _html.escape(str(s))


def _open(h, label):
    return (f'<svg viewBox="0 0 {W} {h}" width="100%" height="auto" '
            f'role="img" aria-label="{_esc(label)}" '
            f'style="display:block;overflow:visible">')


def _text(x, y, s, size=12, fill=MUTED, anchor="start", weight="400"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" '
            f'style="font-variant-numeric:tabular-nums">{_esc(s)}</text>')


def _density_label(v):
    """소수 둘째자리까지 반올림해 불필요한 0만 지운다.

    `:g` 는 33.0 처럼 정수값인 소수를 "33" 으로 지워버려 원본 데이터의
    자릿수 정보(2만원 미만·샛별배송 = 33.0)가 사라진다. 소수점 하나는 항상
    남긴다.
    """
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    if "." not in s:
        s += ".0"
    return s


def pareto_curve(rows):
    """상위 n% 누적 리뷰 점유율. 상위 5%에서 80%를 넘는 것이 요점이다."""
    h, pad_l, pad_r, pad_t, pad_b = 260, 46, 20, 24, 40
    plot_w, plot_h = W - pad_l - pad_r, h - pad_t - pad_b
    out = [_open(h, "상위 n% 상품의 누적 리뷰 점유율")]

    for pct in (0, 25, 50, 75, 100):
        y = pad_t + plot_h * (1 - pct / 100)
        out.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W - pad_r}" y2="{y:.1f}" '
                   f'stroke="{LINE}" stroke-width="1"/>')
        out.append(_text(pad_l - 8, y + 4, f"{pct}%", 11, MUTED, "end"))

    pts = []
    for i, r in enumerate(rows):
        x = pad_l + plot_w * (i / max(len(rows) - 1, 1))
        y = pad_t + plot_h * (1 - r["share"] / 100)
        pts.append((x, y, r))

    out.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts)
               + f'" fill="none" stroke="{ACCENT}" stroke-width="2.5" '
                 'stroke-linejoin="round"/>')
    for x, y, r in pts:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{ACCENT}"/>')
        out.append(_text(x, y - 12, f"{r['share']}%", 12, INK, "middle", "700"))
        out.append(_text(x, h - 20, r["label"], 12, MUTED, "middle"))
        out.append(_text(x, h - 6, f"{r['sku']:,} SKU", 11, MUTED, "middle"))
    out.append("</svg>")
    return "".join(out)


def mirror_bars(rows):
    """품목별 SKU비중(좌) ↔ 리뷰비중(우). 두 폭이 어긋난 정도가 미스매치다."""
    row_h, pad_t = 26, 34
    h = pad_t + row_h * len(rows) + 12
    if not rows:
        return _open(h, "품목별 SKU 비중과 리뷰 비중 대비") + "</svg>"
    rows = sorted(rows, key=lambda r: -r["review_share"])
    mid, gap = W / 2, 62
    half = mid - gap
    scale = max(max(r["sku_share"] for r in rows),
                max(r["review_share"] for r in rows))
    out = [_open(h, "품목별 SKU 비중과 리뷰 비중 대비")]
    out.append(_text(mid - gap / 2 - 4, 16, "SKU 비중", 12, MUTED, "end", "600"))
    out.append(_text(mid + gap / 2 + 4, 16, "리뷰 비중", 12, MUTED, "start", "600"))

    for i, r in enumerate(rows):
        y = pad_t + row_h * i
        cy = y + row_h / 2
        wl = half * (r["sku_share"] / scale)
        wr = half * (r["review_share"] / scale)
        out.append(f'<rect x="{mid - gap / 2 - wl:.1f}" y="{y + 4:.1f}" '
                   f'width="{wl:.1f}" height="{row_h - 10}" rx="2" fill="{SELLER}" '
                   'opacity="0.55"/>')
        out.append(f'<rect x="{mid + gap / 2:.1f}" y="{y + 4:.1f}" '
                   f'width="{wr:.1f}" height="{row_h - 10}" rx="2" fill="{ACCENT}"/>')
        out.append(_text(mid, cy + 4, r["item"], 12, INK, "middle", "600"))
        out.append(_text(mid - gap / 2 - wl - 6, cy + 4, f"{r['sku_share']}%",
                         11, MUTED, "end"))
        out.append(_text(mid + gap / 2 + wr + 6, cy + 4, f"{r['review_share']}%",
                         11, MUTED, "start"))
    out.append("</svg>")
    return "".join(out)


def heatmap_2x2(cells):
    """가격대 × 배송타입 리뷰밀도. 센터피스."""
    cw, ch, pad_l, pad_t = 300, 108, 96, 46
    h = pad_t + ch * 2 + 26
    if not cells:
        return _open(h, "가격대 × 배송타입별 SKU 당 리뷰수") + "</svg>"
    prices = ["2만원 미만", "2만원 이상"]
    dvs = ["샛별배송", "판매자배송"]
    by = {(c["price"], c["delivery"]): c for c in cells}
    top = max(c["density"] for c in cells)

    out = [_open(h, "가격대 × 배송타입별 SKU 당 리뷰수")]
    for j, dv in enumerate(dvs):
        out.append(_text(pad_l + cw * j + cw / 2, 22, dv, 12.5, MUTED, "middle", "600"))
    for i, pr in enumerate(prices):
        out.append(_text(pad_l - 12, pad_t + ch * i + ch / 2 + 4, pr,
                         12.5, MUTED, "end", "600"))

    for i, pr in enumerate(prices):
        for j, dv in enumerate(dvs):
            c = by[(pr, dv)]
            x, y = pad_l + cw * j, pad_t + ch * i
            # 밀도 차가 138배라 선형 배경은 세 칸이 똑같이 비어 보인다. 제곱근 압축으로도
            # 하위 두 칸(0.86, 0.24) 사이 대비가 0.05 밖에 안 벌어져 지수를 0.35 로 낮췄다.
            op = 0.10 + 0.72 * (c["density"] / top) ** 0.35
            out.append(f'<rect x="{x + 3}" y="{y + 3}" width="{cw - 6}" '
                       f'height="{ch - 6}" rx="8" fill="{DAWN}" opacity="{op:.3f}"/>')
            out.append(f'<rect x="{x + 3}" y="{y + 3}" width="{cw - 6}" '
                       f'height="{ch - 6}" rx="8" fill="none" stroke="{LINE}"/>')
            out.append(_text(x + cw / 2, y + ch / 2 - 2,
                             _density_label(c['density']), 30, INK, "middle", "800"))
            out.append(_text(x + cw / 2, y + ch / 2 + 22,
                             f"{c['sku']:,} SKU · 리뷰 {c['reviews']:,}",
                             11.5, MUTED, "middle"))
    out.append(_text(pad_l, h - 4, "칸 안 숫자 = SKU 당 리뷰수", 11, MUTED))
    out.append("</svg>")
    return "".join(out)


def slope(lift_rows):
    """같은 품목을 판매자배송 → 샛별배송으로 옮겼을 때의 리뷰밀도 변화."""
    h, pad_t, pad_b = 300, 40, 44
    if not lift_rows:
        return _open(h, "품목 내 배송타입 전환에 따른 리뷰밀도 변화") + "</svg>"
    plot_h = h - pad_t - pad_b
    x_left, x_right = 190, W - 190
    top = max(r["dawn_density"] for r in lift_rows) * 1.12
    out = [_open(h, "품목 내 배송타입 전환에 따른 리뷰밀도 변화")]
    out.append(_text(x_left, 20, "판매자배송", 12.5, MUTED, "middle", "600"))
    out.append(_text(x_right, 20, "샛별배송", 12.5, MUTED, "middle", "600"))
    out.append(f'<line x1="{x_left}" y1="{pad_t}" x2="{x_left}" '
               f'y2="{pad_t + plot_h}" stroke="{LINE}"/>')
    out.append(f'<line x1="{x_right}" y1="{pad_t}" x2="{x_right}" '
               f'y2="{pad_t + plot_h}" stroke="{LINE}"/>')

    def ypos(v):
        return pad_t + plot_h * (1 - v / top)

    for r in lift_rows:
        y1, y2 = ypos(r["seller_density"]), ypos(r["dawn_density"])
        out.append(f'<line x1="{x_left}" y1="{y1:.1f}" x2="{x_right}" y2="{y2:.1f}" '
                   f'stroke="{ACCENT}" stroke-width="2.5"/>')
        out.append(f'<circle cx="{x_left}" cy="{y1:.1f}" r="4.5" fill="{SELLER}"/>')
        out.append(f'<circle cx="{x_right}" cy="{y2:.1f}" r="5.5" fill="{ACCENT}"/>')
        out.append(_text(x_left - 12, y1 + 4,
                         f"{r['item']} {r['seller_density']:g}", 12.5, INK, "end", "600"))
        out.append(_text(x_right + 12, y2 + 4,
                         f"{r['dawn_density']:g}", 13, INK, "start", "800"))
        out.append(_text(x_right + 12, y2 + 20,
                         f"{round(r['multiple']):g}배", 12, ACCENT, "start", "700"))
    out.append(_text(x_left - 12, h - 12, "숫자 = SKU 당 리뷰수", 11, MUTED, "end"))
    out.append("</svg>")
    return "".join(out)
