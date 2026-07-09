# -*- coding: utf-8 -*-
"""
콜드스타트 추천 미니 데모 (5단계)

신상품 설명 텍스트를 입력하면:
  1. Gemini로 속성 추출 → 코드북 레이블에 맞춰 Semantic ID 부여 (API 1회 호출)
  2. 기존 상품들의 Semantic ID와 속성 유사도 계산
  3. 리뷰가 하나도 없는 신상품인데도 "속성이 비슷한 기존 상품"을 추천

실행: python app_demo.py  →  브라우저에서 http://127.0.0.1:7860 접속
주의: 입력 1건마다 Gemini API 1회 호출 (무료 티어 하루 한도 안에서 사용)
"""

import io
import json
import os
import sys

import gradio as gr
import pandas as pd
from google import genai

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.path.dirname(__file__)
CODEBOOK_PATH = os.path.join(BASE, "data", "codebook_026.json")
PRODUCTS_PATH = os.path.join(BASE, "data", "product_semantic_ids.csv")
MODEL = "gemini-3.1-flash-lite"

# ── 데이터 로드 (앱 시작 시 1회) ──────────────────────────
with open(CODEBOOK_PATH, encoding="utf-8") as f:
    CODEBOOK = json.load(f)
AXES = list(CODEBOOK.keys())
PRODUCTS = pd.read_csv(PRODUCTS_PATH, encoding="utf-8-sig")
# 코드 컬럼을 문자열로 통일 ("2.0" → "2")
for a in AXES:
    PRODUCTS[f"{a}_code"] = (
        PRODUCTS[f"{a}_code"].dropna().astype(float).astype(int).astype(str)
        .reindex(PRODUCTS.index)
    )

# ── 속성 추출 프롬프트: 코드북 레이블 중에서만 고르게 함 ──
def build_prompt(description: str) -> str:
    codebook_lines = []
    for axis, codes in CODEBOOK.items():
        opts = " / ".join(f"{c}:{label}" for c, label in codes.items())
        codebook_lines.append(f"- {axis}: {opts}")
    return f"""당신은 패션 이커머스 속성 분석가입니다.
아래 신상품 설명에서 파악할 수 있는 실착 속성을, 반드시 주어진 코드북의 코드 번호로만 답하세요.

코드북 (축: 코드번호:레이블):
{chr(10).join(codebook_lines)}

규칙:
1. 설명에서 근거를 찾을 수 있는 축만 코드 번호를 부여하고, 알 수 없는 축은 null.
2. 추측 금지. 예: "시원한 냉감 소재" → 촉감 3(시원함), 계절감 1(여름용).
3. JSON 하나만 출력: {{"축이름": "코드번호" 또는 null, ...}}

신상품 설명:
{description}"""


def extract_semantic_id(description: str) -> dict:
    """신상품 설명 → 축별 코드 (Gemini 1회 호출)"""
    client = genai.Client()
    resp = client.models.generate_content(
        model=MODEL,
        contents=build_prompt(description),
        config={"response_mime_type": "application/json"},
    )
    raw = json.loads(resp.text)
    # 코드북에 실제 존재하는 코드만 수용 (환각 방어)
    result = {}
    for axis in AXES:
        code = raw.get(axis)
        if code is not None and str(code) in CODEBOOK[axis]:
            result[axis] = str(code)
    return result


def similarity(new_codes: dict, product_row: pd.Series) -> tuple:
    """신상품과 기존 상품의 속성 유사도.
    둘 다 코드가 있는 축에서 일치 비율 × 비교 가능 축 수 가중치."""
    both, match = 0, 0
    matched_axes = []
    for axis, code in new_codes.items():
        p_code = product_row[f"{axis}_code"]
        if pd.isna(p_code):
            continue
        both += 1
        if str(p_code) == code:
            match += 1
            matched_axes.append(f"{axis}={CODEBOOK[axis][code]}")
    if both == 0:
        return 0.0, ""
    # 일치율에 √(비교축수) 가중 → 겹치는 축이 많은 상품이 근소하게 유리
    score = (match / both) * (both ** 0.5)
    return score, ", ".join(matched_axes)


def subcategory_of(text: str) -> str:
    """텍스트에서 서브카테고리 감지 (상품명/설명 공용)"""
    import re
    t = str(text)
    if re.search(r"파자마|잠옷|홈웨어|라운지", t):
        return "잠옷/홈웨어"
    has_bra = "브라" in t
    has_bottom = bool(re.search(r"팬티|드로즈|트렁크|비키니", t))
    if has_bra and has_bottom:
        return "브라·팬티 세트"
    if has_bra:
        return "브라"
    if has_bottom:
        return "팬티/드로즈"
    return "기타"


def recommend(description: str):
    """Gradio 콜백: 설명 입력 → 속성/Semantic ID/유사 상품 반환"""
    if not description or len(description.strip()) < 10:
        return "⚠ 상품 설명을 10자 이상 입력해주세요.", None

    try:
        new_codes = extract_semantic_id(description)
    except Exception as e:
        return f"⚠ API 호출 실패: {str(e)[:200]}", None

    if not new_codes:
        return "설명에서 실착 속성을 찾지 못했습니다. 소재감/핏/시즌 정보를 담아 입력해보세요.", None

    # 추출된 속성 → Semantic ID 문자열
    short = {"핏": "핏", "착용감": "착", "사이즈감": "사", "기장": "장", "비침": "비",
             "두께": "두", "신축성": "신", "촉감": "촉", "계절감": "계"}
    sem_id = "-".join(f"{short[a]}{c}" for a, c in new_codes.items())
    attrs = "\n".join(f"- **{a}**: {CODEBOOK[a][c]} (코드 {c})" for a, c in new_codes.items())
    header = f"### 추출된 속성\n{attrs}\n\n### Semantic ID: `{sem_id}`"

    # 기존 상품과 유사도 계산 → 상위 5개
    # 설명에서 서브카테고리가 감지되면 같은 카테고리 상품을 우선 정렬
    new_subcat = subcategory_of(description)
    rows = []
    for _, p in PRODUCTS.iterrows():
        score, matched = similarity(new_codes, p)
        if score > 0:
            same_cat = subcategory_of(p["Product Name"]) == new_subcat if new_subcat != "기타" else True
            rows.append({"상품명": p["Product Name"], "유사도": round(score, 2),
                         "일치 속성": matched, "Semantic ID": p["semantic_id"],
                         "리뷰수": p["리뷰수"], "평균평점": p["평균평점"],
                         "_같은카테고리": same_cat})
    if not rows:
        return header + "\n\n유사 상품을 찾지 못했습니다.", None
    top = (pd.DataFrame(rows)
           .sort_values(["_같은카테고리", "유사도"], ascending=[False, False])
           .drop(columns=["_같은카테고리"])
           .head(5).reset_index(drop=True))
    if new_subcat != "기타":
        header += f"\n\n*감지된 카테고리: **{new_subcat}** (같은 카테고리 상품 우선)*"
    return header, top


# ── Gradio UI ─────────────────────────────────────────────
EXAMPLES = [
    "시원한 냉감 원단으로 만든 여름용 심리스 브라. 와이어 없이 편안하게 밀착되고, 신축성이 뛰어나 운동할 때도 좋습니다.",
    "부드러운 모달 소재의 여유핏 반팔 파자마 세트. 얇고 가벼워 여름 잠옷으로 적합합니다.",
    "탄탄한 코튼 스판 소재의 남성 드로즈 5팩. 사계절 착용 가능한 데일리 언더웨어.",
]

with gr.Blocks(title="리뷰 속성 기반 콜드스타트 추천 데모") as demo:
    gr.Markdown(
        "# 리뷰 속성 코드북 기반 콜드스타트 추천 데모\n"
        "신상품은 리뷰가 없어 리뷰 기반 추천이 불가능합니다(콜드스타트). "
        "이 데모는 **상품 설명에서 속성을 추출해 Semantic ID를 부여**하고, "
        "기존 상품의 **리뷰 기반 Semantic ID**와 매칭해 유사 상품을 찾습니다.\n\n"
        "*입력 1건당 Gemini API 1회 호출 · 무신사 속옷/홈웨어 리뷰 523건으로 구축한 코드북 사용*"
    )
    inp = gr.Textbox(label="신상품 설명 입력", lines=4,
                     placeholder="예: 시원한 냉감 원단의 여름용 심리스 브라...")
    btn = gr.Button("속성 추출 & 유사 상품 찾기", variant="primary")
    out_md = gr.Markdown()
    out_df = gr.Dataframe(label="속성이 유사한 기존 상품 TOP 5", interactive=False)
    btn.click(recommend, inputs=inp, outputs=[out_md, out_df])
    gr.Examples(examples=EXAMPLES, inputs=inp)

if __name__ == "__main__":
    demo.launch()
