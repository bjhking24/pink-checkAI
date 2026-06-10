import streamlit as st
import requests
import json
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.figure import Figure
import numpy as np
import time
import base64
import platform
import re
import difflib
from datetime import datetime

# [배포 환경 통합 한글 폰트 대응] 리눅스 서버 및 로컬 환경 완벽 호환
def set_korean_font():
    font_list = fm.findSystemFonts()
    nanum_fonts = [f for f in font_list if 'Nanum' in f]
    if nanum_fonts:
        plt.rcParams['font.family'] = 'NanumGothic'
    elif platform.system() == "Windows":
        plt.rcParams['font.family'] = 'Malgun Gothic'
    elif platform.system() == "Darwin":
        plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()

# 💡 [다른 사람들과 기록을 공유하는 클라우드 DB 연결]
try:
    conn = st.connection("secrets_db", type="sql")
    with conn.session as session:
        session.execute("""
            CREATE TABLE IF NOT EXISTS pinktax_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT,
                name TEXT,
                score INTEGER,
                report TEXT
            );
        """)
        session.commit()
except Exception:
    if "history" not in st.session_state:
        st.session_state.history = []
    conn = None

# [오타 자동 교정 및 제품명 표준화 함수]
def get_standard_name(input_name):
    if not input_name:
        return ""
    test_str = input_name.replace(" ", "").lower()

    standard_products = [
        "비레디 웨이크업 생기 립밤",
        "두바이 쫀득 쿠키",
        "오브제 무드체인지 립밤",
        "질레트 마하3 면도기",
        "페리페라 잉크 브이 쉐딩"
    ]

    standard_map = {p.replace(" ", "").lower(): p for p in standard_products}
    closest_matches = difflib.get_close_matches(test_str, standard_map.keys(), n=1, cutoff=0.5)

    if closest_matches:
        return standard_map[closest_matches[0]]

    if "비레디" in test_str or "비래디" in test_str or "생기립밤" in test_str:
        return "비레디 웨이크업 생기 립밤"
    elif "두바이" in test_str or "두부" in test_str or "쫀득" in test_str or "쫀덕" in test_str:
        return "두바이 쫀득 쿠키"
    elif "페리페라" in test_str or "브이쉐딩" in test_str or "잉크브이" in test_str or "브이섀딩" in test_str:
        return "페리페라 잉크 브이 쉐딩"

    return input_name.strip()

# 5단계 자동차 계기판형 바늘 그래프 생성 함수
def draw_gauge_chart(score=None):
    fig = Figure(figsize=(7, 3.5))
    ax = fig.subplots()
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    sizes = [20, 20, 20, 20, 20, 100]
    colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#900c3f', 'none']

    ax.pie(sizes, colors=colors, startangle=180, counterclock=False, wedgeprops=dict(width=0.3, edgecolor='none'))

    ax.text(-1.15, -0.1, "1. Safe\n(0~20%)", color='#2ecc71', fontsize=10, ha='center', va='top', weight='bold')
    ax.text(-0.85, 0.85, "2. Suspect\n(21~40%)", color='#f1c40f', fontsize=10, ha='center', va='bottom', weight='bold')
    ax.text(0, 1.25, "3. Caution\n(41~60%)", color='#e67e22', fontsize=10, ha='center', va='bottom', weight='bold')
    ax.text(0.85, 0.85, "4. Warning\n(61~80%)", color='#e74c3c', fontsize=10, ha='center', va='bottom', weight='bold')
    ax.text(1.15, -0.1, "5. Severe\n(81~100%)", color='#900c3f', fontsize=10, ha='center', va='top', weight='bold')

    if score is not None:
        angle_rad = np.pi * (1 - score / 100.0)
        needle_length = 0.75
        x = needle_length * np.cos(angle_rad)
        y = needle_length * np.sin(angle_rad)

        ax.plot([0, x], [0, y], color='#34495e', linewidth=4.0, zorder=5)
        ax.plot(0, 0, marker='o', color='#34495e', markersize=12, zorder=6)
        ax.text(0, 0.15, f"{score}%", color='#2c3e50', fontsize=22, ha='center', va='center', weight='bold')

    ax.axis('equal')
    ax.set_xlim(-1.4, 1.4)
    ax.set_ylim(-0.4, 1.5)
    return fig

# API 통신 함수
@st.cache_data(show_spinner=False)
def call_pinktax_api(product_name, product_details, image_bytes, mime_type, ai_provider, model_choice, api_key):
    prompt = f"""
    너는 불필요한 미사여구를 모두 빼고 핵심만 냉철하게 지적하는 독립형 '젠더 마케팅 가격 차별 분석 시스템'이야.
    구글, 제미나이, 오픈라우터 등의 AI 모델 이름을 본문에 절대 언급하지 말고 자체 개발된 전용 알고리즘처럼 행동해.

    [중요 - 실시간 정보 및 주 소비 고객층 검색 지침]
    - 연동된 Internet 검색 도구를 활용하여 현재 온라인상에 유통되는 해당 제품의 '실제 가격', '정가', '성분 및 재질'을 직접 검색해서 알아낼 것.
    - 제품 자체에 '여성용/남성용'이라는 명시적 문구가 없더라도, 사회적·통계적으로 특정 성별이 주 소비 고객층인 제품/서비스인지 분석해내야 함. 주 소비층이 편중되어 있다는 점을 악용해 동급의 일반 유니섹스 제품보다 부당하게 가격을 높게 책정한 '숨겨진 가격 차별(Hidden Tax)' 현상도 철저히 추적할 것.
    - '정보 없음'이나 '알 수 없음'이라는 표현은 절대 사용 금지. 유통 가격과 주 소비층 대역을 파악하여 분석에 반영할 것.

    [🚨 중요 - 대중적 가성비 제품 예외 처리 지침]
    - 만약 분석 대상 제품이 '페리페라 잉크 브이 쉐딩' 혹은 이와 유사하게 인위적인 젠더 프리미엄을 제거하고 g당 단가를 최저 수준으로 공급하는 대중적 가성비 표준 상품인 경우:
      * 이 제품은 위험도가 누적되지 않은 매우 건전한 상품으로 처리함.
      * 최종 위험도 지수는 10% 고정으로 연산하고, 최종 판별은 반드시 [정상적인 원가 반영 상품]으로 귀결시킬 것.
      * '스마트 대안 솔루션' 구역에는 아래 출력 요구 양식을 철저히 따르되 "본 제품은 패키징 및 마케팅 거품을 빼고 단위당 단가를 낮춘 우수한 가성비 표준 제품이므로 현재의 대안 없는 합리적 소비 유지를 강력 권장함."을 명확히 출력할 것.

    [🧪 1. 원재료 및 소재 기준 지식 사전]
    - 화장품/식품: 정제수, 글리세린, 부틸렌글라이콜, 미네랄오일, 밀가루, 설탕 등은 제품의 베이스를 이루는 저가 원료이므로 이들의 단순 용량 증가나 배합은 원가 상승 요인으로 인정하지 않음. 시어버터, 세라마이드, 특수 활성 성분 등이 전성분 상위에 있을 때만 원가 상승 인정.
    - 의류/액세서리/잡화: 실제 사용된 원단(천연 가죽, 면, 폴리에스테르 종류) 및 소재의 퀄리티와 마감 수준을 대조하여 일반 규격 대비 가성비 적정성을 판단.

    [🔍 2. 실시간 교차 검증 및 단가 쪼개기 프로토콜]
    - 검색된 공식몰 정가와 대형 쇼핑몰 실제 판매가(할인가)를 교차 검증해 분석.
    - 1+1, 세트, 묶음 상품의 경우 반드시 총액을 개수로 나눈 '순수 1개당 단가'를 계산하여 기준으로 삼음.

    [🚨 3. 성별 오류 방지 및 주 소비층 분기 규칙]
    - 남성이 주 소비층이거나 '남성 마케팅'으로 단가 거품이 발견될 경우 최종 판별에 절대로 '핑크택스 현상'을 출력해서는 안 되며, 반드시 [비합리적 젠더 마케팅 의심 상품 (블루택스 현상)]으로 분리.
    - 여성이 주 소비층이거나 '여성 마케팅'으로 거품이 발견될 경우 [비합리적 젠더 마케팅 의심 상품 (핑크택스 현상)]으로 판별.
    - 성별 편중 없이 합리적이라면 [정상적인 원가 반영 상품]으로 판별.

    [📊 4. 위험도 지수 산출 수식 알고리즘 (0% 시작, 감점 누적 방식)]
    다음 3가지 항목의 감점 점수를 합산하여 최종 위험도 지수 퍼센트(%)를 연산하라. (단, 가성비 예외 처리 제품은 20% 미만 고정)
    - 소재/성분 및 기능 거품 (+최대 40%): 두 성별 제품 간 성분/스펙 차이가 없는데 가격 차이가 나면 +40% 누적.
    - 마케팅 및 타겟팅 거품 (+최대 30%): 주 소비 고객층의 성별 편중성 및 라벨을 노려 프리미엄을 붙인 경우 +30% 누적.
    - 용량/사이즈 꼼수 (+최대 30%): 용량 쪼개기, 패키징 변경으로 단위당 가격 왜곡 시 +30% 누적.
    - 최종 공식: 위험도 지수 = 성분 거품 점수 + 마케팅 거품 점수 + 용량 꼼수 점수

    [🚨 5. 대학생 스마트 대안 소비 가이드 - V.I.A 표준 추천 DB 매칭 규칙]
    - 아래의 [V.I.A 공인 대안 소비 매트릭스] 데이터를 기반으로 사용자가 입력한 상품군에 정밀 매칭되는 실제 대안 브랜드 및 구체적 제품명을 '스마트 대안 솔루션' 란에 확실하게 명시하여 제안할 것.

    [📌 V.I.A 공인 대안 소비 매트릭스 데이터베이스]
    - 헤어 살롱 컷 프리미엄 의심 시 ➔ 대안처: '차홍룸' (남녀 커트 구분 없이 직급별 디자인 컷 단일 정찰제) 또는 '블루클럽 / 레드폴 바버샵' (성별 추가금 없는 대안)
    - 헤어 픽서 및 스프레이 거품 의심 시 ➔ 대안처: '가스비(GATSBY)', '다슈(DASHU)' (ml당 단가 거품이 빠진 남성용 강력 하드 스프레이/픽서 교차 활용)
    - 두피/탈모 샴푸 거품 의심 시 ➔ 대안처: '알페신 카페인 샴푸 C1' (성별 마케팅 배제, 핵심 원료 집중)
    - 트리트먼트 및 에센스 용기/모델료 거품 의심 시 ➔ 대안처: '아론샵(Aaron)', '아모스프로페셔널' (대용량 살롱 전용 원료 배치)
    - 스킨케어 (기초/에센스/크림) 거품 의심 시 ➔ 대안처: '디오디너리' (원료 중심 에센스 완벽 대체), '코스알엑스', '시드물', 'VT코스메틱 / 마데카21' (다이소몰 입점 핵심 원료 집중) 및 '폴라스초이스(PAULA'S CHOICE)' (성별보다 피부타입 최우선 고려)
    - 색조 화장품 (립밤/쿠션/컨투어) 거품 의심 시 ➔ 대안처: '비레디 웨이크업 생기 립밤', '오브제 무드체인지 립밤' (비싼 여성용 프리미엄 라벨 대체), '라카(Laka)', '태그(TAG, 다이소)' (성별 디자인 거품이 차단된 젠더 뉴트럴 브랜드)
    - 면도기 및 바디케어/생활용품 제모 거품 의심 시 ➔ 대안처: '와이즐리 센시티브 면도기', '질레트 마하3/프로글라이드 면도기', '도루코 페이스6 면도기', '니베아 맨 쉐이빙 젤/폼' 및 '해리스(HARRY'S)' (기능 위주 설계 글로벌 가성비 표준 브랜드)
    - 향수 및 프리미엄 바디 핑크택스 의심 시 ➔ 대안처: '이솝(Aesop)' (에센셜 설계), '바이레도(Byredo)' (성별 라벨링 배제 향 본연 가치 중심)
    - 의류 핑크택스 의심 시 ➔ 대안처: '이자벨마랑 남녀 복합 매장 동일 컬렉션', '유니클로 유니섹스 라인 섹션', '나이키 스타일 홍대 지점 / 나이키 코리아 성인공용 카테고리', '뉴에라' (성별 페이지를 나누지 않거나 동일 가격 책정)

    [분석 대상 제품 및 정보]
    - 제품명: {product_name if product_name else '사용자가 사진 제공함'}
    - 추가 상세 정보: {product_details if product_details else '없음'}

    [출력 요구 양식 - 기밀 퓨샷 형식을 준수하며, 이모티콘은 전면 금지하고, 개조식 명사형 종결어미(~함, ~됨)를 사용할 것]
    ### 젠더 마케팅 진단 대시보드
    - 분석 대상 제품명: [명확한 제품명 및 카테고리 분류]
    - 추정 주 소비 고객층: [예: 여성 80% / 남성 70% / 유니섹스 등 추정치 표기]
    - 위험도 지수: [위 연산 기준에 따른 결과값]%
    - 최종 판별: [비합리적 젠더 마케팅 의심 상품 (핑크택스 현상) / 비합리적 젠더 마케팅 의심 상품 (블루택스 현상) / 정상적인 원가 반영 상품 중 택일]
    - 제품 정가: [검색된 정가 표기 (묶음 상품일 경우 '총액(개당 약 X원)' 형태로 반드시 병기)]
    - 분석 기준 가격: [검색된 실판매가 표기 (묶음 상품일 경우 '총액(개당 약 X원)' 형태로 반드시 병기)]

    ---
    ### 3대 가이드라인 분석 결과
    1. 소재/성분 및 기능성: [카테고리에 맞는 원단, 성분, 소재 및 기능 분석 1~2줄 요약]
    2. 마케팅 및 타겟팅 프리미엄: [명시적 라벨 혹은 '주 소비층 편중'을 이용한 가격 거품 여부 분석 1~2줄 요약]
    3. 용량/사이즈 대비 가격: [g/ml/개수 단위당 가격 꼼수 및 왜곡 여부 1~2줄 요약]

    ---
    ### 스마트 대안 솔루션
    - [단순히 저가 상품 추종 지양. 성별 프레임을 허물고 본질적 가치에 집중하는 주체적 소비 마인드를 바탕으로, 위 V.I.A 공인 대안 소비 매트릭스에 맵핑된 실제 추천 브랜드/제품명을 정확히 명시하며 마케팅 거품을 우회할 수 있는 명확한 실무적 행동 가이드라인을 1~2줄로 단도직입적 기술. 단, 가성비 예외 상품일 경우 예외 처리 지침 구역의 문구를 토출할 것]
    """

    if ai_provider == "Google Gemini":
        parts = [{"text": prompt}]
        if image_bytes and mime_type:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({"inlineData": {"mimeType": mime_type, "data": b64_image}})

        models_to_try = [model_choice, "gemini-2.5-flash" if model_choice == "gemini-2.5-pro" else "gemini-2.5-pro"]
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
            payload = {
                "contents": [{"parts": parts}],
                "tools": [{"googleSearch": {}}],
                "generationConfig": {"temperature": 0.0}
            }
            for attempt in range(3):
                try:
                    response = requests.post(url, headers=headers, json=payload)
                    response_json = response.json()
                    if "error" in response_json:
                        err_msg = response_json["error"].get("message", "")
                        err_code = response_json["error"].get("code", 0)
                        if err_code == 503 or "high demand" in err_msg.lower() or "overloaded" in err_msg.lower():
                            time.sleep(1.5 + attempt)
                            continue
                        break
                    if "candidates" in response_json:
                        return {"text": response_json['candidates'][0]['content']['parts'][0]['text']}
                except Exception:
                    time.sleep(1)
                    continue
        return {"error": "트래픽 폭증으로 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."}

    elif ai_provider == "OpenRouter (Gemma 2)":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_choice,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            response_json = response.json()
            if "choices" in response_json:
                return {"text": response_json['choices'][0]['message']['content']}
            elif "error" in response_json:
                return {"error": response_json["error"].get("message", "통신 중 에러가 발생했습니다.")}
        except Exception as e:
            return {"error": f"통신 실패: {e}"}

# --- 메인 웹 화면 구성 ---
st.title("PINK-Check AI")

st.markdown("<h4 style='font-weight: 500; color: #555555; margin-bottom: 15px;'>AI 활용 젠더 마케팅 판별 시스템</h4>", unsafe_allow_html=True)

st.markdown("""
<div style="background-color: #FFF5F7; border: 1px solid #FF1493; border-left: 6px solid #FF1493; padding: 16px; border-radius: 6px; margin-top: 10px; margin-bottom: 20px;">
    <p style="color: #FF1493; margin: 0 0 6px 0; font-weight: bold; font-size: 17px;">💡 핑크택스(Pink Tax)란?</p>
    <p style="color: #333333; margin: 0; line-height: 1.6; font-size: 14.5px;">
        동일한 성분, 기능, 용량의 제품·서비스임에도 단순히 <b>'여성용'</b> 마케팅 라벨이나 디자인이 적용되었다는 이유로 가격이 더 비싸지는 <b>성별 기반 가격 차별 현상</b>을 뜻합니다.<br>
        <small style="color: #777777; font-style: italic;">(이와 반대로 남성향 마케팅으로 가격 거품을 형성하는 현상은 '블루택스'라고 합니다.)</small>
    </p>
</div>
""", unsafe_allow_html=True)

st.caption("※ 시스템 이용 유의사항: 본 프로그램의 분석 결과는 자체 지식 지표와 알고리즘에 기반한 추정치입니다. 제조사의 실시간 가격 변동 및 성분 리뉴얼에 따라 미세한 차이가 발생할 수 있으므로 참고용 데이터로만 활용해 주시기 바랍니다.")

with st.sidebar:
    st.header("프로젝트 정보")
    st.subheader("세계와 시민 (GCP 프로젝트)")
    st.markdown("---")
    st.write("**개발 및 기획 팀: V.I.A**")
    st.markdown("---")

    ai_provider = st.selectbox(
        "메인 AI 엔진 선택 (실시간 검색은 Gemini 권장)",
        ["Google Gemini", "OpenRouter (Gemma 2)"]
    )

    if ai_provider == "Google Gemini":
        # 🛠️ index를 1에서 0으로 변경하여 gemini-2.5-flash가 기본으로 열리도록 수정
        model_choice = st.selectbox("분석 모델", ["gemini-2.5-flash (빠른 모델)", "gemini-2.5-pro (정확한 모델)"], index=0)
    else:
        model_choice = st.selectbox("분석 모델", ["google/gemma-2-27b-it"], index=0)

# 화면 탭 구성
tab1, tab2, tab3 = st.tabs(["제품 판독", "판독 기록", "판독 기준 안내"])

# --- 1번 탭: 제품 판별기 ---
with tab1:
    if ai_provider == "Google Gemini":
        product_name_input = st.text_input("제품명을 입력하세요 (사진 업로드 시 생략 가능)", placeholder="")
        uploaded_file = st.file_uploader("제품 사진, 성분표 또는 라벨을 업로드하세요", type=["jpg", "jpeg", "png"])
    else:
        product_name_input = st.text_input("제품명을 입력하세요", placeholder="")
        uploaded_file = None

    product_details = st.text_area("가격, 용량(중량), 주 소비 고객층에 대해 아시는 정보나 의견을 적어주세요 (선택사항)", placeholder="")

    if st.button("분석 시작"):
        final_product_name = get_standard_name(product_name_input)

        if not final_product_name and not uploaded_file:
            st.warning("제품명을 입력하거나 제품 사진을 업로드해 주세요.")
        elif ai_provider == "OpenRouter (Gemma 2)" and not final_product_name:
            st.warning("제품명을 입력해 주세요.")
        else:
            with st.spinner("AI가 주 소비층 통계와 구글 검색 결과를 바탕으로 통합 분석하고 있습니다..."):
                image_bytes = None
                mime_type = None
                if uploaded_file is not None:
                    image_bytes = uploaded_file.read()
                    mime_type = uploaded_file.type

                if ai_provider == "Google Gemini":
                    api_key = st.secrets["GEMINI_API_KEY"]
                else:
                    api_key = st.secrets["OPENROUTER_API_KEY"]

                result = call_pinktax_api(final_product_name, product_details, image_bytes, mime_type, ai_provider, model_choice, api_key)

                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success("분석이 완료되었습니다.")
                    ai_text = result["text"]

                    score_value = 10 

                    try:
                        score_match = re.search(r"위험도\s*지수\s*:\s*(\d+)\s*%", ai_text)
                        if score_match:
                            score_value = int(score_match.group(1))
                        else:
                            score_match_alt = re.search(r"(\d+)\s*%", ai_text)
                            if score_match_alt:
                                score_value = int(score_match_alt.group(1))
                    except Exception:
                        score_value = 10

                    fig_res = draw_gauge_chart(score_value)
                    st.pyplot(fig_res)

                    st.markdown(ai_text)

                    log_name = final_product_name
                    if not log_name:
                        name_match = re.search(r"분석\s*대상\s*제품명\s*:\s*([^\n\s\],]+)", ai_text)
                        if name_match:
                            log_name = name_match.group(1).strip()
                        else:
                            log_name = "식별된 사진 분석 상품"

                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    if conn is not None:
                        try:
                            with conn.session as session:
                                session.execute(
                                    "INSERT INTO pinktax_history (time, name, score, report) VALUES (:time, :name, :score, :report);",
                                    {"time": current_time, "name": log_name, "score": score_value, "report": ai_text}
                                )
                                session.commit()
                        except Exception:
                            pass
                    else:
                        st.session_state.history.append({
                            "time": current_time, "name": log_name, "score": score_value, "report": ai_text
                        })

                    st.markdown("---")
                    st.caption("본 분석 리포트는 알고리즘 기반 예측물이며 법적 효력을 가지지 않습니다.")

# --- 2번 탭: 판독 기록 히스토리 ---
with tab2:
    st.header("판독 기록")
    st.write("AI가 분석한 내역이 기록됩니다.")

    history_to_display = []
    if conn is not None:
        try:
            df = conn.query("SELECT time, name, score, report FROM pinktax_history;", ttl=0)
            history_to_display = df.to_dict(orient="records")
        except Exception:
            history_to_display = list(st.session_state.history)
    else:
        history_to_display = list(st.session_state.history)

    if not history_to_display:
        st.info("아직 분석 기록이 없습니다.")
    else:
        col_sort1, col_sort2, col_del = st.columns([2, 2, 1])

        with col_sort1:
            sort_criteria = st.selectbox("정렬 기준", ["시간 순", "ㄱㄴㄷ 순", "위험도 순"])
        with col_sort2:
            sort_order = st.selectbox("정렬 방향", ["내림차순", "오름차순"])
        with col_del:
            st.write("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            if st.button("데이터 비우기"):
                if conn is not None:
                    try:
                        with conn.session as session:
                            session.execute("DELETE FROM pinktax_history;")
                            session.commit()
                    except Exception:
                        pass
                else:
                    st.session_state.history = []
                st.rerun()

        st.markdown("---")

        if sort_criteria == "시간 순":
            sort_key = lambda x: x['time']
        elif sort_criteria == "ㄱㄴㄷ 순":
            sort_key = lambda x: x['name']
        elif sort_criteria == "위험도 순":
            sort_key = lambda x: x['score']

        is_reverse = True if sort_order == "내림차순" else False
        history_to_display.sort(key=sort_key, reverse=is_reverse)

        for entry in history_to_display:
            with st.expander(f"[{entry['time']}] {entry['name']} — 위험도 지수: {entry['score']}%"):
                st.write(f"**진단 일시:** {entry['time']}")
                st.write(f"**제품명:** {entry['name']}")
                st.write(f"**위험도 지수:** {entry['score']}%")
                st.markdown(entry['report'])

# --- 3번 탭: 판별 기준 안내 ---
with tab3:
    st.markdown("## 시스템 판독 기준 및 알고리즘 안내")
    st.write("본 시스템은 '주 소비 고객층의 성별 편중성'을 악용한 숨겨진 마케팅 거품을 공정하게 진단하기 위해 **4단계 검증 과정**을 거칩니다.")
    st.markdown("---")
    st.write("**[ 위험도 단계 표준 그래프 ]**")
    fig_guide = draw_gauge_chart()
    st.pyplot(fig_guide)
    st.markdown("---")

    st.subheader("검증 과정 4단계")
    st.markdown("""
    **1. 실시간 구글 검색 및 주 소비층 추론**
    인터넷에 유통되는 실시간 정가/판매가를 추적함과 동시에, 해당 제품군이 통계적·사회적으로 특정 성별에 치우친 카테고리인지 다각도로 분석합니다.

    **2. 단위당 가격 및 본질 가치 비교**
    단순히 겉모습이나 라벨의 유무를 떠나, 동급의 남녀공용 제품 혹은 일반 제품과 단위 중량당 단가 또는 기능적 소요 원가를 환산하여 철저히 비교합니다.

    **3. 과거 사례 대조**
    각 산업 카테고리별로 축적된 정상 제품 데이터와 마케팅 거품 제품 데이터를 바탕으로 일관된 잣대를 적용합니다.

    **4. 젠더 타겟팅 거품 교차 검증**
    여성 소비층 제품에 부과되는 숨겨진 핑크택스뿐만 아니라, 남성 소비층 제품에 붙는 숨겨진 블루택스 현상까지 동등한 기준으로 추적합니다.
    """)
