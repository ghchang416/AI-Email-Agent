import streamlit as st
import pandas as pd
import html
from datetime import datetime
import client
from components import apply_custom_styles

# --- 1. 페이지 기본 설정 ---
st.set_page_config(
    page_title="Ajou Intelligent Email",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. 커스텀 스타일 적용 ---
apply_custom_styles()

# --- 3. 데이터 로딩 및 처리 ---
try:
    tasks = client.get_tasks()
    users = client.get_users()
    is_online = True
except Exception:
    tasks = []
    users = []
    is_online = False

total_tasks = len(tasks)
todo_tasks = len([t for t in tasks if t['status'] == '시작 전'])
in_progress_tasks = len([t for t in tasks if t['status'] == '진행 중'])
done_tasks = len([t for t in tasks if t['status'] == '완료'])
active_users = len([u for u in users if u.get('status') == '업무 중'])

# --- 4. 메인 UI 레이아웃 ---

# (1) 헤더 및 시스템 상태
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("Dashboard")
    st.markdown(
        f"""
        <div style="color: #6B7280; margin-top: -10px; font-size: 1.1rem;">
        AI Agent 기반 이메일 자동 응답 및 분류 시스템 현황판
        </div>
        """, 
        unsafe_allow_html=True
    )

with col_h2:
    # 시스템 상태 표시기
    status_color = "#10B981" if is_online else "#EF4444"
    status_text = "SYSTEM ONLINE" if is_online else "SYSTEM OFFLINE"
    st.markdown(
        f"""
        <div style="
            display: flex; align-items: center; justify-content: flex-end; gap: 8px; 
            padding: 10px; background: white; border-radius: 8px; border: 1px solid #E5E7EB;">
            <span style="width: 10px; height: 10px; background-color: {status_color}; border-radius: 50%; box-shadow: 0 0 8px {status_color};"></span>
            <span style="font-weight: 700; color: #374151; font-size: 0.9rem;">{status_text}</span>
        </div>
        """, 
        unsafe_allow_html=True
    )

st.markdown("---")

# (2) 핵심 지표 (KPI Cards)
col1, col2, col3, col4 = st.columns(4)

def metric_box(label, value, sub_value, color_border):
    st.markdown(
        f"""
        <div style="
            background: white; padding: 20px; border-radius: 12px; 
            border: 1px solid #E5E7EB; border-left: 5px solid {color_border};
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
            <div style="color: #6B7280; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">{label}</div>
            <div style="font-size: 2rem; font-weight: 800; color: #111827; margin: 5px 0;">{value}</div>
            <div style="font-size: 0.8rem; color: #9CA3AF;">{sub_value}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

with col1:
    metric_box("Pending Requests", str(todo_tasks), "처리 대기 중인 메일", "#6366F1") # Indigo
with col2:
    metric_box("Processing", str(in_progress_tasks), "AI 에이전트 분석 중", "#3B82F6") # Blue
with col3:
    metric_box("Completed Today", str(done_tasks), "자동 응답 완료", "#10B981") # Green
with col4:
    metric_box("Active Agents", str(active_users), "현재 가동 중인 멤버", "#F59E0B") # Amber

st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

# (3) 메인 콘텐츠 영역 (2단 분리)
c_main1, c_main2 = st.columns([2, 1])

with c_main1:
    st.subheader("Recent Activities")
    if not tasks:
        st.info("표시할 최근 활동 내역이 없습니다.")
    else:
        recent_tasks = sorted(tasks, key=lambda x: x.get('id', 0), reverse=True)[:5]
        
        for task in recent_tasks:
            icon = "📩" if task['status'] == '시작 전' else ("⚙️" if task['status'] == '진행 중' else "✅")
            bg_color = "#F9FAFB"
            
            safe_email = html.escape(task.get('sender_email', 'Unknown'))
            
            st.markdown(
                f"""
                <div style="
                    background: {bg_color}; padding: 12px 16px; border-radius: 8px; margin-bottom: 8px;
                    border: 1px solid #F3F4F6; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 1.2rem;">{icon}</span>
                        <div>
                            <div style="font-weight: 600; color: #374151;">{task['title']}</div>
                            <div style="font-size: 0.8rem; color: #6B7280;">From: {safe_email}</div>
                        </div>
                    </div>
                    <span style="
                        font-size: 0.75rem; padding: 4px 8px; border-radius: 999px; 
                        background: white; border: 1px solid #E5E7EB; color: #4B5563;">
                        {task['status']}
                    </span>
                </div>
                """, 
                unsafe_allow_html=True
            )

with c_main2:
    st.subheader("Quick Actions")
    
    with st.container():
        st.markdown(
            """
            <div style="background: #1F2937; color: white; padding: 20px; border-radius: 12px; margin-bottom: 15px;">
                <div style="font-weight: 600; margin-bottom: 5px;">🚀 Go to Kanban Board</div>
                <div style="font-size: 0.85rem; color: #9CA3AF; margin-bottom: 15px;">
                    할당된 업무를 확인하고 AI 초안을 검토하세요.
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    st.info("👈 사이드바 메뉴를 통해\n\n'할당된 업무' 또는 '사용자 관리' 페이지로 이동하여 작업을 수행하세요.")

# --- 사이드바 ---
st.sidebar.markdown("### 📧 App Navigation")
st.sidebar.caption(f"Current Time: {datetime.now().strftime('%H:%M')}")