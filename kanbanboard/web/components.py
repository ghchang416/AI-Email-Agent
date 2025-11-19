# components.py

import streamlit as st
import html
from typing import Dict, Any
import client

def apply_custom_styles():
    """앱 전체에 적용할 모던하고 세련된 커스텀 CSS"""
    st.markdown("""
    <style>
        /* ... (기존 폰트 및 레이아웃 CSS 유지) ... */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1F2937;
        }
        .stApp { background-color: #F3F4F6; }
        [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E5E7EB; }
        
        /* --- [수정됨] 수신 메일 박스 스타일 --- */
        .received-mail-container {
            background-color: #F9FAFB;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 12px;
            margin-top: 10px;
            margin-bottom: 15px;
        }
        
        .received-mail-label {
            font-size: 0.75rem;
            color: #6B7280;
            font-weight: 700; /* 좀 더 진하게 */
            text-transform: uppercase;
            margin-bottom: 8px;
            letter-spacing: 0.05em;
        }

        /* 본문 내용 스크롤 처리 */
        .received-mail-content {
            font-size: 0.9rem;
            color: #374151;
            line-height: 1.5;
            white-space: pre-wrap; /* 줄바꿈 유지 */
            max-height: 250px;     /* 너무 길면 스크롤 */
            overflow-y: auto;      /* 세로 스크롤 허용 */
            background-color: #FFFFFF; /* 본문 배경 흰색으로 강조 */
            padding: 10px;
            border-radius: 6px;
            border: 1px dashed #E5E7EB;
        }
        
        /* ... (나머지 버튼, 카드 스타일 등은 기존 그대로 유지) ... */
        .css-card { background-color: #FFFFFF; padding: 1.5rem; border-radius: 12px; border: 1px solid #E5E7EB; }
        button[kind="primary"] { background-color: #2563EB; border: none; }
    </style>
    """, unsafe_allow_html=True)

def metric_card(label: str, value: str, icon: str = ""):
    st.markdown(
        f"""
        <div style="background-color: white; border: 1px solid #E5E7EB; border-radius: 10px; padding: 15px 20px; display: flex; flex-direction: column; height: 100%;">
            <div style="font-size: 0.85rem; color: #6B7280; font-weight: 500; margin-bottom: 4px;">{icon} {label}</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #111827;">{value}</div>
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
    """모던한 스타일의 칸반 카드 렌더링 (HTML 구조 개선)"""
    
    task_key_prefix = f"task_{task['id']}"
    
    safe_sender_name = html.escape(task.get('sender_name', 'N/A'))
    safe_sender_email = html.escape(task.get('sender_email', 'N/A'))
    raw_content = task.get('received_mail_content', '') or ""
    safe_content = html.escape(raw_content)
    
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

    st.markdown(
        f"""
        <div class="received-mail-container">
            <div class="received-mail-label">ORIGINAL MESSAGE</div>
            <div class="received-mail-content">{safe_content}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True) 
    
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
            
            if assignee_name and assignee_name in user_names:
                a_idx = user_names.index(assignee_name)
            else:
                a_idx = 0
                
            new_assignee_name = st.selectbox(
                "Assignee",
                options=user_names,
                index=a_idx,
                key=f"{task_key_prefix}_assignee_form",
                disabled=is_done
            )
    
        st.markdown("<div style='margin: 12px 0;'></div>", unsafe_allow_html=True)

        if is_done:
            if st.form_submit_button("↩️ Reopen Task", use_container_width=True):
                payload = task.copy()
                payload['status'] = '진행 중'
                # 필요한 필드만 남기거나 전체 업데이트 (API 스펙에 맞게)
                update_data = {k: v for k, v in payload.items() if k != 'id'}
                if client.update_task_api(task['id'], update_data):
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