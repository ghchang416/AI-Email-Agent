import streamlit as st
import html
from typing import Dict, Any
import client

def apply_custom_styles():
    """앱 전체에 적용할 모던하고 세련된 커스텀 CSS (사이드바 포함)"""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1F2937;
        }

        /* --- 메인 컨테이너 스타일 --- */
        .stApp {
            background-color: #F3F4F6;
        }
        
        /* --- 사이드바 스타일 --- */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E5E7EB;
        }
        
        [data-testid="stSidebar"] .block-container {
            padding-top: 2rem;
        }

        [data-testid="stSidebarNav"] span {
            font-size: 0.95rem;
            font-weight: 500;
            color: #4B5563;
        }

        h1 {
            font-size: 2rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }

        /* --- 카드 스타일 --- */
        .css-card {
            background-color: #FFFFFF;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #E5E7EB;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            margin-bottom: 1.5rem;
        }

        [data-testid="stDataEditor"] {
            border-radius: 8px;
            border: 1px solid #E5E7EB;
            overflow: hidden;
        }

        /* --- KPI 메트릭 카드 --- */
        .metric-card {
            background-color: white;
            border: 1px solid #E5E7EB;
            border-radius: 10px;
            padding: 15px 20px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #6B7280;
            font-weight: 500;
            margin-bottom: 4px;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #111827;
        }
        
        /* 버튼 스타일 */
        button[kind="primary"] {
            background-color: #2563EB;
            border: none;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
            transition: all 0.2s;
        }
        button[kind="primary"]:hover {
            background-color: #1D4ED8;
            box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3);
        }
        
        /* 칸반 헤더 */
        .kanban-header {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.01em;
        }
        
        .header-todo { background-color: #F3F4F6; color: #4B5563; border-left: 4px solid #9CA3AF; }
        .header-doing { background-color: #EFF6FF; color: #1E40AF; border-left: 4px solid #3B82F6; }
        .header-done { background-color: #ECFDF5; color: #065F46; border-left: 4px solid #10B981; }

        .badge-count {
            background-color: rgba(255,255,255,0.6);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-left: auto;
        }
        
        .received-mail-container {
            background-color: #F9FAFB;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 12px;
            margin-top: 8px;
        }
        .received-mail-label {
            font-size: 0.75rem;
            color: #6B7280;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

    </style>
    """, unsafe_allow_html=True)

def metric_card(label: str, value: str, icon: str = ""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{icon} {label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

def draw_task_card(
    task: Dict[str, Any], 
    user_map: Dict, 
    user_names: list, 
    user_name_map: Dict, 
    is_done: bool = False
):
    """모던한 스타일의 칸반 카드 (로그 상세 보기 버튼 추가)"""
    
    task_key_prefix = f"task_{task['id']}"
    
    # 데이터 안전 처리
    safe_sender_name = html.escape(task.get('sender_name', 'N/A'))
    safe_sender_email = html.escape(task.get('sender_email', 'N/A'))
    raw_content = task.get('received_mail_content', '') or ""
    safe_content = html.escape(raw_content)
    
    # 발신자 정보
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:6px; font-size:0.85rem; color:#6B7280; margin-bottom:8px;">
            <span style="background:#EFF6FF; color:#1D4ED8; padding:2px 6px; border-radius:4px; font-weight:500;">From</span>
            <span style="font-weight:500; color:#111827;">{safe_sender_name}</span>
            <span style="color:#9CA3AF;">&lt;{safe_sender_email}&gt;</span>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # 수신 메일 본문 (요약)
    st.markdown(
        f"""
        <div class="received-mail-container">
            <div class="received-mail-label">ORIGINAL MESSAGE</div>
            <div style="max-height: 150px; overflow-y: auto; font-size: 0.9rem; color: #374151; white-space: pre-wrap;">{safe_content}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # --- 로그 분석 페이지 이동 버튼 ---
    if st.button("🔍 View AI Reasoning Logs", key=f"btn_log_{task['id']}", use_container_width=True):
        st.query_params["task_id"] = str(task['id'])
        st.switch_page("pages/task_logs.py")

    st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True) 
    
    # 3. 폼 영역
    with st.form(key=f"form_{task_key_prefix}"):
        
        st.markdown("**✍️ Reply Draft**")
        new_draft = st.text_area(
            "메일 초안 수정:", 
            value=task.get('draft_content', ''), 
            height=120, 
            key=f"{task_key_prefix}_draft_form",
            disabled=is_done,
            label_visibility="collapsed",
            placeholder="AI가 작성한 초안을 수정하세요..."
        )
        
        st.markdown("<div style='margin: 8px 0;'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            status_options = ["시작 전", "진행 중", "완료"]
            current_status = task.get('status', '시작 전')
            idx = status_options.index(current_status) if current_status in status_options else 0
            
            new_status = st.selectbox(
                "Status",
                options=status_options,
                index=idx,
                key=f"{task_key_prefix}_status_form",
                disabled=is_done
            )

        with c2:
            assignee_id = task.get('assignee_id')
            assignee_name = user_map.get(assignee_id)
            a_idx = user_names.index(assignee_name) if assignee_name in user_names else 0
                
            new_assignee_name = st.selectbox(
                "Assignee",
                options=user_names,
                index=a_idx,
                key=f"{task_key_prefix}_assignee_form",
                disabled=is_done
            )
    
        st.markdown("<div style='margin: 12px 0;'></div>", unsafe_allow_html=True)

        # 액션 버튼
        if is_done:
            if st.form_submit_button("↩️ Reopen Task", use_container_width=True):
                payload = task.copy()
                payload['status'] = '진행 중'
                del payload['id']
                if client.update_task_api(task['id'], payload):
                    st.success("재오픈 성공"); st.rerun()
        else:
            b1, b2 = st.columns(2)
            with b1:
                if st.form_submit_button("💾 Save", use_container_width=True):
                    payload = task.copy()
                    payload['status'] = new_status
                    payload['assignee_id'] = user_name_map.get(new_assignee_name)
                    payload['draft_content'] = new_draft
                    del payload['id']
                    if client.update_task_api(task['id'], payload):
                        st.toast("저장 완료", icon="✅"); st.rerun()
            
            with b2:
                if st.form_submit_button("🚀 Send", type="primary", use_container_width=True):
                    payload = task.copy()
                    payload['status'] = '완료'
                    payload['assignee_id'] = user_name_map.get(new_assignee_name)
                    payload['draft_content'] = new_draft
                    del payload['id']
                    if client.update_task_api(task['id'], payload):
                        st.balloons(); st.rerun()