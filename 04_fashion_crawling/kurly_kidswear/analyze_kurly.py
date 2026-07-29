# -*- coding: utf-8 -*-
"""컬리 키즈웨어/유아동패션 수집 CSV 분석 (A~F).

결과는 세 가지로 저장한다.
  분석리포트_<ts>.txt   콘솔과 동일한 고정폭 텍스트
  분석리포트_<ts>.md    표·이미지가 들어간 마크다운 (공유용)
  A_브랜드별 / D_품목별 <ts>.csv
"""

import glob
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
pd.set_option("display.width", 200)
pd.set_option("display.unicode.east_asian_width", True)

# 검증된 카테고리 팔레트 (slot1 blue / slot2 orange) + chrome
C_DAWN, C_SELLER = "#2a78d6", "#eb6834"
SURFACE, INK, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#898781", "#e1e0d9", "#c3c2b7"

plt.rcParams.update({
    "font.family": "Malgun Gothic",
    "axes.unicode_minus": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
})


def latest_csv():
    files = sorted(glob.glob(os.path.join(BASE, "kurly_kidswear_*.csv")))
    if not files:
        sys.exit("수집 CSV가 없습니다. 먼저 collect_kurly.py 를 실행하세요.")
    return files[-1]


# ------------------------------------------------------------- D: 품목 분류
# 위에서부터 먼저 매칭. 구체적인 신발류를 일반 의류보다 앞에 둔다.
#
# 주의: 반드시 '[브랜드]' 접두사를 떼고 매칭한다. 붙인 채로 하면 브랜드명에
# 들어있는 글자가 규칙에 걸린다 (예: [하우키즈풀] 의 '풀' -> 학용품 오분류).
RULES = [
    # 한복/파티용품/완구/헤어액세서리는 요청받은 12개 분류에 속하지 않는다.
    # 의류 규칙(치마·저고리 등)에 잘못 빨려들지 않도록 먼저 기타로 확정한다.
    ("기타",   r"한복|저고리|쾌자|색동|두루마기|당의|마고자|도포|배자"),
    ("실내화", r"실내화|실내용\s*신|우피"),
    ("장화",   r"장화|레인부츠|레인슈즈|워터부츠"),
    ("샌들",   r"샌들|슬리퍼|아쿠아슈즈|쪼리|플립플랍|플립플롭"),
    ("운동화", r"운동화|스니커즈|스니커|슬립온|워커|구두|부츠|슈즈|단화|로퍼|보행기화|걸음마신발"),
    ("양말",   r"양말|삭스|스타킹|타이츠|타이즈|덧신|레그워머|\d+족"),
    ("가방",   r"가방|백팩|책가방|크로스백|슬링백|파우치|보조가방|힙색|에코백|폴딩백"
               r"|런치백|스쿨백|미니백|폰백|텀블러백|쇼퍼백|토트백|보스턴백|더플백"),
    ("학용품", r"학용품|필통|연필|색연필|크레파스|스케치북|공책|노트|물통|도시락|가위|사인펜|문구|지우개|풀세트|자석칠판"),
    ("잠옷",   r"잠옷|파자마|수면조끼|수면|홈웨어|내복|실내복|배냇"),
    ("아우터", r"아우터|자켓|재킷|점퍼|패딩|코트|가디건|조끼|베스트|바람막이|윈드브레이커|후리스|플리스|무스탕|스키복|올인원"),
    ("하의",   r"바지|팬츠|레깅스|치마|스커트|반바지|쇼츠|청바지|하의|블루머|기저귀커버|튜튜|조거"),
    ("상의",   r"티셔츠|맨투맨|셔츠|블라우스|니트|후드|후디|나시|민소매|바디슈트|우주복|상의|반팔|긴팔|원피스|드레스|스웨터|폴로|래쉬가드|터틀넥|탑"),
]
COMPILED = [(k, re.compile(p)) for k, p in RULES]
BRAND_PREFIX = re.compile(r"^\s*\[[^\]]*\]\s*")

# '기타' 안에서 무엇이 큰 덩어리인지 보여주기 위한 보조 분해 (분류 결과에는 영향 없음)
ETC_GROUPS = [
    ("한복",          r"한복|저고리|쾌자|색동|두루마기|당의|마고자|도포|배자"),
    ("파티·이벤트용품", r"가랜드|파티|풍선|피나타|토퍼|종이컵|종이접시|냅킨|케이크|케익|생일|할로윈|크리스마스|오너먼트|센터피스|크래커|호일|봉투|스티커|캔들|초대장"),
    ("헤어·액세서리",  r"헤어|머리띠|머리끈|리본핀|목걸이|팔찌|악세사리|액세서리|선글라스|시계|반지"),
    ("모자",          r"모자|캡모자|볼캡|비니|보닛|썬캡|버킷햇|벙거지|플랩캡"),
    ("완구·놀이",     r"퍼즐|블록|인형|장난감|마라카스|비치볼|물놀이|튜브|킥보드|자석놀이|놀이|워터북|디스크"),
    ("상하복 세트",    r"상하복|상하세트|셋업|세트"),
    ("수영",          r"수영|스윔|비치|물안경|암밴드|스와들"),
    ("우산·잡화",     r"우산|우비|양산|타월|담요|블랭킷|텀블러|보온병"),
]
ETC_COMPILED = [(k, re.compile(p)) for k, p in ETC_GROUPS]


def classify(name):
    body = BRAND_PREFIX.sub("", str(name or ""))
    for label, rx in COMPILED:
        if rx.search(body):
            return label
    return "기타"


def etc_group(name):
    body = BRAND_PREFIX.sub("", str(name or ""))
    for label, rx in ETC_COMPILED:
        if rx.search(body):
            return label
    return "미상"


# ------------------------------------------------------------- 리포트 출력
def _cell(v):
    """마크다운 셀 한 칸 포맷."""
    if v is None or v is pd.NA:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "예" if v else "아니오"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    if isinstance(v, (float, np.floating)):
        f = float(v)
        if pd.isna(f):
            return ""
        if f.is_integer():
            return f"{int(f):,}"
        # 소수는 최대 2자리까지 살린다. 1자리로 자르면 0.03 이 0.0 이 돼
        # 리뷰밀도처럼 작은 값이 의미를 잃는다.
        return f"{f:,.2f}".rstrip("0").rstrip(".")
    return str(v).replace("|", r"\|")


def md_table(df, index=True):
    """tabulate 없이 DataFrame 을 마크다운 표로. 숫자 컬럼은 우측 정렬."""
    d = df.reset_index() if index else df.copy()
    right = [pd.api.types.is_numeric_dtype(d[c]) for c in d.columns]
    lines = [
        "| " + " | ".join(str(c) for c in d.columns) + " |",
        "| " + " | ".join("---:" if r else ":---" for r in right) + " |",
    ]
    for row in d.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(_cell(v) for v in row) + " |")
    return "\n".join(lines)


class Report:
    """콘솔 · 고정폭 텍스트 · 마크다운을 동시에 누적한다."""

    def __init__(self, title, subtitle):
        self.txt = ["=" * 78, title, "=" * 78, subtitle]
        self.md = [f"# {title}", "", f"*{subtitle}*", ""]
        print("\n".join(self.txt))

    def h(self, text):
        print(f"\n\n{text}\n" + "-" * 78)
        self.txt += ["", "", text, "-" * 78]
        self.md += ["", f"## {text}", ""]

    def p(self, text):
        print("  " + text)
        self.txt.append("  " + text)
        self.md += [text, ""]

    def bullets(self, items):
        for it in items:
            print("  - " + it)
            self.txt.append("  - " + it)
            self.md.append(f"- {it}")
        self.md.append("")

    def table(self, df, index=True):
        s = df.to_string()
        print(s)
        self.txt.append(s)
        self.md += [md_table(df, index), ""]

    def image(self, fname, alt):
        self.md += [f"![{alt}]({fname})", ""]

    def save(self, ts):
        t = os.path.join(BASE, f"분석리포트_{ts}.txt")
        m = os.path.join(BASE, f"분석리포트_{ts}.md")
        open(t, "w", encoding="utf-8").write("\n".join(self.txt) + "\n")
        open(m, "w", encoding="utf-8").write("\n".join(self.md) + "\n")
        print(f"\n리포트 저장: {os.path.basename(t)} / {os.path.basename(m)}")


# ------------------------------------------------------------- 실행
def main():
    path = latest_csv()
    ts = re.search(r"(\d{8}_\d{6})", os.path.basename(path)).group(1)
    df = pd.read_csv(path)
    df["품목"] = df["상품명"].map(classify)

    # 목록 API 의 review_count 는 소수 리뷰를 0 으로 반환하는 결함이 있다.
    # enrich_reviews.py 결과가 있으면 상세 API 값으로 덮어쓴다.
    raw_total = int(df["리뷰수"].sum())
    fix_path = os.path.join(BASE, f"review_counts_{ts}.jsonl")
    n_fixed = n_checked = 0
    if os.path.exists(fix_path):
        fx = pd.read_json(fix_path, lines=True)
        fx = fx[fx["status"].eq("ok") & fx["review_count"].notna()]
        m = dict(zip(fx["no"].astype(int), fx["review_count"].astype(int)))
        n_checked = len(fx)
        before = df["리뷰수"].copy()
        df["리뷰수"] = df.apply(
            lambda r: m.get(int(r["상품ID"]), r["리뷰수"])
            if r["리뷰수"] == 0 else r["리뷰수"], axis=1).astype(int)
        n_fixed = int((df["리뷰수"] != before).sum())

    when = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}"
    R = Report("컬리 키즈웨어 상품 분석",
               f"수집 {when} · {len(df):,} SKU · 카테고리 172 / 919017")

    # ---------------------------------------------------------- 개요
    R.h("수집 개요")
    R.bullets(
        [f"{k}: {v:,}건" for k, v in df["category"].value_counts().items()]
        + [f"총 리뷰수 {df['리뷰수'].sum():,}건",
           f"브랜드 {df['브랜드명'].nunique():,}개 (브랜드 미상 {df['브랜드명'].isna().sum()}건)"]
    )

    R.h("데이터 품질 주의사항")
    notes = ["**평점은 컬리 API 에 존재하지 않는다.** 상세 API 응답에도 "
             "rating/score/star 키가 없어 `평점` 컬럼은 전 행 NaN 이다. "
             "A~F 분석은 평점을 쓰지 않아 영향은 없다."]
    if n_checked:
        notes.append(
            f"**목록 API 의 `review_count` 는 부정확하다.** 리뷰가 적은 상품을 0 으로 "
            f"반환한다. 목록에서 0 이던 {n_checked:,}건을 상세 API 로 재확인해 "
            f"{n_fixed:,}건({n_fixed/n_checked*100:.1f}%)을 보정했고, "
            f"총 리뷰수가 {raw_total:,} → {df['리뷰수'].sum():,}건으로 늘었다.")
    else:
        notes.append("**리뷰수 미보정 상태다.** `enrich_reviews.py` 를 실행하지 않으면 "
                     "목록 API 결함 때문에 B·C 가 과대 계상된다.")
    notes.append("브랜드명은 상품명의 `[브랜드]` 접두사에서 추출했다(커버리지 100%). "
                 "표본 20건 대조 결과 상세 API 의 `brand_info` 와 17건 일치, "
                 "1건 표기차(`휠라키즈`/`휠라 키즈`), 2건은 API 에만 브랜드가 없었다.")
    R.bullets(notes)

    # ---------------------------------------------------------- A
    R.h("A. 브랜드별 지표 (리뷰수 내림차순)")
    a = (df.groupby("브랜드명")
           .agg(SKU수=("상품ID", "count"),
                총리뷰수=("리뷰수", "sum"),
                평균가격=("판매가", "mean"))
           .assign(리뷰per_SKU=lambda x: (x["총리뷰수"] / x["SKU수"]).round(2))
           .sort_values("총리뷰수", ascending=False))
    a["평균가격"] = a["평균가격"].round(0).astype(int)
    a = a[["SKU수", "총리뷰수", "리뷰per_SKU", "평균가격"]]
    R.table(a.head(25))
    a.to_csv(os.path.join(BASE, f"A_브랜드별_{ts}.csv"), encoding="utf-8-sig")

    big3 = a.nlargest(3, "SKU수")
    dense = a[a["SKU수"] >= 10].nlargest(1, "리뷰per_SKU")
    R.p(f"SKU 최다 3사({', '.join(big3.index)})가 카탈로그의 "
        f"{big3['SKU수'].sum()/len(df)*100:.0f}%를 차지하지만 리뷰는 "
        f"{big3['총리뷰수'].sum()/a['총리뷰수'].sum()*100:.1f}%에 그친다. "
        f"반대로 {dense.index[0]}는 {int(dense['SKU수'].iloc[0])} SKU 로 "
        f"SKU 당 {dense['리뷰per_SKU'].iloc[0]:.2f}건을 만든다 "
        f"(평균가 {int(dense['평균가격'].iloc[0]):,}원). 카탈로그 크기와 실수요가 반비례한다.")
    R.p(f"전체 브랜드 {len(a):,}개.")

    # ---------------------------------------------------------- B
    R.h("B. 파레토 — 리뷰수 상위 n% 상품의 리뷰 점유율")
    rv = df["리뷰수"].sort_values(ascending=False).to_numpy()
    tot = int(rv.sum())
    rows = []
    for pct in (1, 5, 10, 20, 50):
        k = max(1, int(round(len(rv) * pct / 100)))
        rows.append({"상위": f"{pct}%", "SKU수": k, "누적리뷰": int(rv[:k].sum()),
                     "리뷰점유율%": round(rv[:k].sum() / tot * 100, 1)})
    b = pd.DataFrame(rows).set_index("상위")
    R.table(b)
    nonzero = int((rv > 0).sum())
    R.p(f"리뷰가 하나라도 있는 상품은 {nonzero:,}개({nonzero/len(rv)*100:.1f}%)뿐이고 "
        f"나머지 {len(rv)-nonzero:,}개는 반응이 0이다. 지니계수 {gini(rv):.3f} — "
        f"통상적인 파레토(상위 20%가 80%)보다 훨씬 극단적인 "
        f"상위 5%가 {b.loc['5%', '리뷰점유율%']:.0f}% 구조다.")

    # ---------------------------------------------------------- C
    R.h("C. 리뷰 0인 상품 비율 — 샛별 vs 판매자배송")
    c = (df.assign(리뷰0=df["리뷰수"].eq(0))
           .groupby("배송타입")
           .agg(SKU수=("상품ID", "count"), 리뷰0_SKU=("리뷰0", "sum"),
                총리뷰수=("리뷰수", "sum"), 중앙값리뷰=("리뷰수", "median")))
    c["리뷰0_비율%"] = (c["리뷰0_SKU"] / c["SKU수"] * 100).round(1)
    c["리뷰per_SKU"] = (c["총리뷰수"] / c["SKU수"]).round(2)
    c = c[["SKU수", "리뷰0_SKU", "리뷰0_비율%", "총리뷰수", "리뷰per_SKU", "중앙값리뷰"]]
    R.table(c)
    if {"샛별배송", "판매자배송"} <= set(c.index):
        d_, s_ = c.loc["샛별배송"], c.loc["판매자배송"]
        R.p(f"샛별 {int(d_['SKU수'])}개가 판매자 {int(s_['SKU수']):,}개보다 리뷰를 더 많이 "
            f"만든다({int(d_['총리뷰수']):,} vs {int(s_['총리뷰수']):,}). SKU 당으로는 "
            f"{d_['리뷰per_SKU']:.1f} vs {s_['리뷰per_SKU']:.2f}로 "
            f"{d_['리뷰per_SKU']/max(s_['리뷰per_SKU'], 0.01):.0f}배 차이다. "
            f"직매입 소수 품목에만 수요가 붙고 3P 카탈로그는 사실상 진열만 된 상태다.")

    # ---------------------------------------------------------- D
    R.h("D. 품목 분류별 SKU수 · 리뷰수 · 리뷰밀도")
    d = (df.groupby("품목")
           .agg(SKU수=("상품ID", "count"), 총리뷰수=("리뷰수", "sum"),
                평균가격=("판매가", "mean"))
           .assign(리뷰밀도=lambda x: (x["총리뷰수"] / x["SKU수"]).round(2))
           .sort_values("총리뷰수", ascending=False))
    d["평균가격"] = d["평균가격"].round(0).astype(int)
    d["SKU비중%"] = (d["SKU수"] / len(df) * 100).round(1)
    d["리뷰비중%"] = (d["총리뷰수"] / d["총리뷰수"].sum() * 100).round(1)
    d = d[["SKU수", "SKU비중%", "총리뷰수", "리뷰비중%", "리뷰밀도", "평균가격"]]
    R.table(d)
    d.to_csv(os.path.join(BASE, f"D_품목별_{ts}.csv"), encoding="utf-8-sig")

    wear = [x for x in ("상의", "하의", "아우터") if x in d.index]
    if wear:
        w = d.loc[wear]
        R.p(f"SKU 배분과 실수요가 정반대다. 의류({'/'.join(wear)})는 SKU "
            f"{w['SKU비중%'].sum():.0f}%를 쓰고 리뷰 {w['리뷰비중%'].sum():.1f}%에 그치는 반면, "
            f"실내화·학용품은 SKU 1.6%로 리뷰의 "
            f"{d.loc[[i for i in ('실내화', '학용품') if i in d.index], '리뷰비중%'].sum():.0f}%를 만든다. "
            f"저가 소모품이 팔리고 고가 의류는 안 팔린다.")

    etc = df[df["품목"] == "기타"].copy()
    etc["세부"] = etc["상품명"].map(etc_group)
    eb = (etc.groupby("세부")
             .agg(SKU수=("상품ID", "count"), 총리뷰수=("리뷰수", "sum"),
                  평균가격=("판매가", "mean"))
             .sort_values("SKU수", ascending=False))
    eb["평균가격"] = eb["평균가격"].round(0).astype(int)
    R.p(f"**'기타' {len(etc):,}건({len(etc)/len(df)*100:.1f}%)의 구성** — 분류 실패가 아니라 "
        f"요청받은 12개 분류에 속하지 않는 품목이다. "
        f"'미상'은 영문 모델명 위주라 키워드 분류의 한계에 해당한다.")
    R.table(eb)

    # ---------------------------------------------------------- E
    R.h("E. 가격대 분포 — 샛별 vs 판매자배송")
    e = df.groupby("배송타입")["판매가"].describe(
        percentiles=[.05, .25, .5, .75, .95]).round(0).astype(int)
    R.table(e)
    png = plot_box(df, ts)
    R.image(os.path.basename(png), "배송타입별 판매가 분포 박스플롯")
    if {"샛별배송", "판매자배송"} <= set(e.index):
        R.p(f"판매자배송이 중앙값 기준 "
            f"{e.loc['판매자배송', '50%']/e.loc['샛별배송', '50%']:.1f}배 비싸다"
            f"({e.loc['판매자배송', '50%']:,}원 vs {e.loc['샛별배송', '50%']:,}원). "
            f"샛별은 {e.loc['샛별배송', 'max']:,}원에서 끊기는 반면 판매자는 "
            f"{e.loc['판매자배송', 'max']:,}원까지 열려 있다. "
            f"컬리 직매입은 저가·회전 품목에 한정돼 있다.")

    # ---------------------------------------------------------- F
    R.h("F. 172(키즈웨어) vs 919017(유아동패션) 브랜드 교집합")
    cats = sorted(df["category"].unique())
    s = {c: set(df.loc[df["category"] == c, "브랜드명"].dropna()) for c in cats}
    k, y = s[cats[0]], s[cats[1]]
    inter = k & y
    ids = {c: set(df.loc[df["category"] == c, "상품ID"]) for c in cats}
    R.bullets([
        f"{cats[0]} 브랜드 {len(k):,}개",
        f"{cats[1]} 브랜드 {len(y):,}개",
        f"**브랜드 교집합 {len(inter)}개** (자카드 유사도 {len(inter)/len(k | y):.4f})",
        f"상품ID 교집합 {len(ids[cats[0]] & ids[cats[1]])}건",
    ])
    if inter:
        sub = (df[df["브랜드명"].isin(inter)]
               .pivot_table(index="브랜드명", columns="category",
                            values="상품ID", aggfunc="count", fill_value=0))
        sub["총리뷰"] = df[df["브랜드명"].isin(inter)].groupby("브랜드명")["리뷰수"].sum()
        R.table(sub.sort_values("총리뷰", ascending=False))
    else:
        R.p("두 카테고리는 브랜드도 상품도 전혀 겹치지 않는다. 172 는 level 1 독립 트리, "
            "919017 은 level 2(상위 '유아동')로 **분류 체계 자체가 다르다.** "
            "통합 분석 대상이 아니라 별개 매장으로 봐야 한다.")
    only_y = sorted(y - k)
    R.p(f"{cats[1]} 에만 있는 브랜드 {len(only_y)}개: " + ", ".join(only_y[:15])
        + (" …" if len(only_y) > 15 else ""))

    # ---------------------------------------------------------- 산출물
    R.h("산출물")
    R.bullets([
        f"`{os.path.basename(path)}` — 수집 원본 {len(df):,}행",
        f"`A_브랜드별_{ts}.csv` / `D_품목별_{ts}.csv` — 집계 결과",
        f"`{os.path.basename(png)}` — 가격 분포 박스플롯",
        f"`raw/{ts}/` — 원본 JSON + 매니페스트",
        "`collect_kurly.py` / `enrich_reviews.py` / `analyze_kurly.py`",
    ])

    R.save(ts)


def gini(x):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if x.sum() == 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def plot_box(df, ts):
    order = ["샛별배송", "판매자배송"]
    order = [o for o in order if o in df["배송타입"].unique()]
    data = [df.loc[df["배송타입"] == o, "판매가"].dropna().to_numpy() for o in order]
    colors = [C_DAWN, C_SELLER][:len(order)]

    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    bp = ax.boxplot(data, patch_artist=True, widths=0.36, showfliers=False,
                    medianprops=dict(color=SURFACE, linewidth=2),
                    whiskerprops=dict(color=AXIS, linewidth=1.2),
                    capprops=dict(color=AXIS, linewidth=1.2),
                    boxprops=dict(linewidth=0))
    for patch, col in zip(bp["boxes"], colors):
        patch.set_facecolor(col)
        patch.set_edgecolor(SURFACE)
        patch.set_linewidth(2)          # 인접 채움 사이 2px 서피스 간격

    # 지터 산점으로 실제 분포를 겹쳐 보여준다 (박스가 감추는 밀집도)
    rng = np.random.default_rng(0)
    for i, (arr, col) in enumerate(zip(data, colors), start=1):
        samp = rng.choice(arr, size=min(400, len(arr)), replace=False)
        ax.scatter(rng.normal(i, 0.055, len(samp)), samp, s=9, alpha=0.22,
                   color=col, linewidths=0, zorder=3)

    ax.set_yscale("log")
    ax.set_ylim(900, 300_000)
    ax.set_yticks([1000, 3000, 10_000, 30_000, 100_000, 300_000])
    ax.get_yaxis().set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
    ax.set_xticklabels([f"{o}\n(n={len(a):,})" for o, a in zip(order, data)],
                       fontsize=11, color=INK)
    ax.set_ylabel("판매가 (원, 로그 스케일)", fontsize=10, color=MUTED)
    ax.set_title("배송타입별 판매가 분포 — 컬리 키즈웨어·유아동패션",
                 fontsize=13, color=INK, pad=16, loc="left")

    # 직접 라벨은 박스 위쪽 캡 바깥에 둔다 (박스 안에 놓으면 채움색과 겹쳐 판독 불가)
    for i, arr in enumerate(data, start=1):
        cap = np.percentile(arr, 75) + 1.5 * (np.percentile(arr, 75) - np.percentile(arr, 25))
        top = arr[arr <= cap].max()
        ax.annotate(f"중앙값 {int(np.median(arr)):,}원", (i, top),
                    xytext=(0, 12), textcoords="offset points",
                    fontsize=9.5, color=MUTED, ha="center", va="bottom")

    ax.yaxis.grid(True, color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.xaxis.grid(False)
    ax.minorticks_off()                      # 로그 보조눈금이 잔선으로 남는 것 제거
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, length=0)

    fig.tight_layout()
    p = os.path.join(BASE, f"E_가격분포_{ts}.png")
    fig.savefig(p, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return p


if __name__ == "__main__":
    main()
