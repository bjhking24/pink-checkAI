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

# 💡 [오직 현재 사용자의 기록만 남기는 로컬 세션 저장소 초기화]
if "history" not in st.session_state:
    st.session_state.history = []

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

# API 통신 함수 (속도 최적화 프롬프트 적용)
@st.cache_data(show_spinner=False)
def call_pinktax_api(product_name, product_details, image_bytes, mime_type, ai_provider, model_choice, api_key):
    prompt = f"""
    너는 불필요한 미사여구 없이 핵심만 냉철하게 지적하는 독립형 '젠더 마케팅 가격 차별 분석 시스템'이야.
    구글, 제미나이 등 AI 모델 이름을 본문에 절대 언급하지 말고 전용 알고리즘처럼 행동해.

    [🎯 필수 지침: 실시간 검색 및 주 소비층 추론]
    1. 반드시 연동된 Internet 검색 도구를 활용하여 해당 제품의 '실제 온라인 유통 가격', '정가', '성분/재질'을 직접 검색해서 알아낼 것.
    2. 제품 자체에 명시적 문구가 없더라도 사회적·통계적으로 특정 성별이 주 소비층인 제품인지 분석하여, 주 소비층 편중을 악용한 '숨겨진 가격 차별(Hidden Tax)'까지 철저히 추적할 것. ('정보 없음' 사용 금지)

    [🚨 가성비 제품 예외 처리]
    - '페리페라 잉크 브이 쉐딩' 등 마케팅 거품을 빼고 g당 단가를 최저 수준으로 공급하는 가성비 표준 상품은 위험도 10% 고정, [정상적인 원가 반영 상품]으로 판별할 것.

    [📊 위험도 지수 산출 규칙]
    아래 3가지 요소를 종합하여 0~100% 사이의 위험도 지수를 도출하라.
    - 소재/성분 및 기능 거품 (최대 40%) / 마케팅 및 타겟팅 거품 (최대 30%) / 용량/사이즈 꼼수 (최대 30%)

    [📌 V.I.A 대안 소비 매트릭스 (참조용)]
    - 헤어컷: 차홍룸(정찰제), 블루클럽 / 픽서·스프레이: 가스비, 다슈 / 탈모샴푸: 알페신 C1
    - 스킨케어: 디오디너리, 코스알엑스, 시드물, VT코스메틱(다이소), 폴라스초이스
    - 색조: 비레디 웨이크업 생기 립밤, 오브제 무드체인지 립밤, 라카, 태그(다이소)
    - 면도기: 와이즐리 센시티브 면도기, 질레트 마하3/프로글라이드, 도루코 페이스6
    - 향수·바디: 이솝, 바이레도 / 의류: 유니클로 유니섹스, 나이키 성인공용, 뉴에라
    (위 매트릭스에서 입력 상품과 매칭되는 실제 브랜드/제품을 찾아 대안으로 제시할 것)

    [분석 대상]
    - 제품명: {product_name if product_name else '사용자가 사진 제공함'}
    - 추가 정보: {product_details if product_details else '없음'}

    [출력 요구 양식 - 이모티콘 금지, 개조식 명사형 종결어미(~함, ~됨) 사용]
    ### 젠더 마케팅 진단 대시보드
    - 분석 대상 제품명: [제품명 및 카테고리 분류]
    - 추정 주 소비 고객층: [예: 여성 80% / 남성 70% / 유니섹스 등]
    - 위험도 지수: [결과값]%
    - 최종 판별: [비합리적 젠더 마케팅 의심 상품 (핑크택스 현상) / 비합리적 젠더 마케팅 의심 상품 (블루택스 현상) / 정상적인 원가 반영 상품 중 택일]
    - 제품 정가: [검색된 정가 (묶음은 '총액(개당 약 X원)')]
    - 분석 기준 가격: [검색된 실판매가 (묶음은 '총액(개당 약 X원)')]

    ---
    ### 3대 가이드라인 분석 결과
    1. 소재/성분 및 기능성: [성분, 소재 및 기능 분석 1~2줄 요약]
    2. 마케팅 및 타겟팅 프리미엄: [가격 거품 여부 분석 1~2줄 요약]
    3. 용량/사이즈 대비 가격: [단위당 가격 왜곡 여부 1~2줄 요약]

    ---
    ### 스마트 대안 솔루션
    - [위 매트릭스에 기반한 실제 추천 브랜드/제품명과 마케팅 거품 우회 가이드를 1~2줄로 기술. 가성비 예외 상품은 "본 제품은 가성비 표준 제품이므로 현재의 합리적 소비 유지를 강력 권장함." 출력]
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
        # 🛠️ index=0 설정으로 gemini-2.5-flash가 기본 활성화됨
        model_choice = st.selectbox("분석 모델", ["gemini-2.5-flash (빠른 모델)", "gemini-2.5-pro (정확한 모델)"], index=0)
    else:
        model_choice = st.selectbox("분석 모델", ["google/gemma-2-27b-it"], index=0)

# 화면 탭 구성
tab1, tab2, tab3 = st.tabs(["제품 판독", "내 판독 기록", "판독 기준 안내"])

# --- 1번 탭: 제품 판별기 ---
with tab1:
    if ai_provider == "Google Gemini":
        product_name_input = st.text_input("제품명을 입력하세요 (사진 업로드 시 생략 가능)", placeholder="")
        uploaded_file = st.file_uploader("제품 사진 또는 성분표 업로드하세요", type=["jpg", "jpeg", "png"])
    else:
        product_name_input = st.text_input("제품명을 입력하세요", placeholder="")
        uploaded_file = None

    product_details = st.text_area("가격, 용량(중량), 주 소비층에 대한 정보 정보나 의견을 적어주세요 (선택사항)", placeholder="")

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

                    # 💡 [오직 현재 브라우저 세션의 history에만 안전하게 기록 노출]
                    st.session_state.history.append({
                        "time": current_time, "name": log_name, "score": score_value, "report": ai_text
                    })

                    st.markdown("---")
                    st.caption("본 분석 리포트는 알고리즘 기반 예측물이며 법적 효력을 가지지 않습니다.")

# --- 2번 탭: 판독 기록 히스토리 ---
with tab2:
    st.header("나의 판독 기록")
    st.write("이번 세션에서 내가 분석한 내역이 기록됩니다. (브라우저를 새로고침하면 초기화됩니다.)")

    # 💡 [외부 공유 DB 조회를 완전 제거하여 오직 개인 세션 데이터만 표출]
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
            if st.button("내 기록 비우기"):
                # 💡 [공용 데이터 삭제가 아닌 오직 나만의 브라우저 세션 초기화]
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
