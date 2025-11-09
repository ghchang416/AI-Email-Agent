import streamlit as st
from components import apply_custom_styles

# --- 1. 페이지 기본 설정 ---
st.set_page_config(
    page_title="지능형 이메일 칸반보드",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. 커스텀 스타일 적용 ---
apply_custom_styles()

# --- 3. 사이드바 설정 ---
st.sidebar.title("📧 Ajou Email Process")
st.sidebar.info("메뉴에서 페이지를 선택하세요.")

# --- 4. 메인 페이지 (소개) ---
st.title("지능형 이메일 칸반보드")
st.markdown("사이드바에서 **'할당된 업무'** 또는 **'사용자 관리'** 페이지를 선택하여 작업을 시작하세요.")
st.image("https://images.unsplash.com/photo-1588702547919-26089e690ecc?q=80&w=2070",
         caption="AI 기반 이메일 처리 자동화 대시보드")