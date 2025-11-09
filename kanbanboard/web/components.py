# streamlit_app/ui_components.py

import streamlit as st
from typing import Dict, Any
import client

def apply_custom_styles():
    """앱 전체에 적용할 커스텀 CSS"""
    st.markdown("""
    <style>
        /* ... (이전과 동일한 CSS) ... */
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
        }
        [data-testid="stSidebar"] { padding-top: 1.5rem; }
        [data-testid="stSidebarNav"] ul { padding-top: 1rem; }
        [data-testid="stSidebarNav"] li { font-size: 1.1rem; margin-bottom: 0.5rem; }
        [data-testid="stVerticalBlock"] > [data-testid="stExpander"] {
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            background-color: #FFFFFF;
        }
        [data-testid="stVerticalBlock"] > [data-testid="stExpander"] [data-testid="stExpanderHeader"] {
            font-size: 1rem;
            font-weight: 500;
            padding-top: 15px;
            padding-bottom: 15px;
        }
        [data-testid="stVerticalBlock"] > [data-testid="stExpander"] [data-testid="stExpanderHeader"] p {
            font-weight: 500;
        }
        .column-title {
            font-size: 1.1rem;
            font-weight: 600;
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 1rem;
            display: inline-block;
        }
        .title-todo { background-color: #F3E8FF; }
        .title-doing { background-color: #E6F3FF; }
        .title-done { background-color: #E3F8E9; }

        /* [추가] 수신된 메일 본문 영역 스타일 */
        .received-mail-box {
            background-color: #FAFAFA;
            border: 1px dashed #DDDDDD;
            padding: 10px;
            border-radius: 5px;
            margin-top: 5px;
            margin-bottom: 15px;
        }
        .received-mail-box textarea {
            background-color: #FAFAFA !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
def draw_task_card(
    task: Dict[str, Any], 
    user_map: Dict, 
    user_names: list, 
    user_name_map: Dict, 
    is_done: bool = False
):
    """칸반보드의 개별 태스크 카드를 그립니다."""
    
    task_key_prefix = f"task_{task['id']}"
    
    st.caption(f"From: {task.get('sender_name', 'N/A')} <{task.get('sender_email', 'N/A')}>")
    with st.container(border=True):
         st.markdown("**수신된 메일 본문**")
         st.text_area(
             "Received Mail",
             value=task.get('received_mail_content', '내용 없음'), 
             height=100, 
             key=f"{task_key_prefix}_received", 
             disabled=True,
             label_visibility="collapsed"
         )
    
    st.divider()
    
    with st.form(key=f"form_{task_key_prefix}"):
        
        # --- 메일 초안 ---
        st.markdown("**메일 초안 수정 (Agent 생성안)**")
        new_draft = st.text_area(
            "메일 초안 수정:", 
            value=task['draft_content'], 
            height=150, 
            key=f"{task_key_prefix}_draft_form",
            disabled=is_done,
            label_visibility="collapsed"
        )
        
        # --- 상태 변경 ---
        status_options = ["시작 전", "진행 중", "완료"]
        try:
            current_status_index = status_options.index(task['status'])
        except ValueError:
            current_status_index = 0 
            
        new_status = st.selectbox(
            "상태 변경:",
            options=status_options,
            index=current_status_index,
            key=f"{task_key_prefix}_status_form",
            disabled=is_done
        )
        
        # --- 담당자 변경 ---
        assignee_index = user_names.index(user_map[task['assignee_id']]) if task['assignee_id'] in user_map else 0
        new_assignee_name = st.selectbox(
            "담당자 변경:",
            options=user_names,
            index=assignee_index,
            key=f"{task_key_prefix}_assignee_form",
            disabled=is_done
        )
    
        # --- 버튼 로직 ---
        if is_done:
            if st.form_submit_button("'진행 중'으로 되돌리기", key=f"{task_key_prefix}_reopen"):
                
                update_payload = {
                    "title": task['title'],
                    "status": "진행 중",
                    "assignee_id": task['assignee_id'],
                    "sender_name": task.get('sender_name'),
                    "sender_email": task.get('sender_email'),
                    "received_mail_content": task.get('received_mail_content'),
                    "message_id": task.get('message_id'),
                    "draft_content": task['draft_content'] # 되돌릴 때는 초안 수정사항 반영 안 함
                }
                
                if client.update_task_api(task['id'], update_payload):
                    st.success(f"'{task['title']}' 작업을 '진행 중'으로 변경했습니다.")
                    st.rerun()
                else:
                    st.error("작업 상태 변경에 실패했습니다.")
        else:
            # --- [시작 전 / 진행 중] 버튼 ---
            col_btn1, col_btn2 = st.columns([1, 1])
            
            with col_btn1:
                if st.form_submit_button("변경 사항 저장", key=f"{task_key_prefix}_save"):
                    
                    update_payload = {
                        "title": task['title'],
                        "status": new_status,
                        "assignee_id": user_name_map.get(new_assignee_name, task['assignee_id']),
                        "sender_name": task.get('sender_name'),
                        "sender_email": task.get('sender_email'),
                        "received_mail_content": task.get('received_mail_content'),
                        "message_id": task.get('message_id'),
                        "draft_content": new_draft
                    }
                    
                    if client.update_task_api(task['id'], update_payload):
                        st.success(f"'{task['title']}' 작업이 업데이트되었습니다.")
                        st.rerun()
                    else:
                        st.error("작업 업데이트에 실패했습니다.")
            
            with col_btn2:
                if st.form_submit_button("✅ 최종 검토 및 완료", key=f"{task_key_prefix}_reply", type="primary"):
                    
                    update_payload = {
                        "title": task['title'],
                        "status": "완료",
                        "assignee_id": user_name_map.get(new_assignee_name, task['assignee_id']),
                        "sender_name": task.get('sender_name'),
                        "sender_email": task.get('sender_email'),
                        "received_mail_content": task.get('received_mail_content'),
                        "message_id": task.get('message_id'),
                        "draft_content": new_draft
                    }
                    
                    if client.update_task_api(task['id'], update_payload):
                        st.success(f"'{task['title']}' 작업을 '완료' 처리합니다.")
                        st.rerun()
                    else:
                        st.error("작업 상태 업데이트에 실패했습니다.")
