# kanban_board.py

import streamlit as st
import client
from components import draw_task_card, apply_custom_styles

st.set_page_config(layout="wide", page_title="AI Agent Workflow", page_icon="🤖")

# 커스텀 CSS 적용
apply_custom_styles()

# --- 헤더 영역 ---
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.title("Task Board")
    st.caption("AI Agent가 분석한 이메일 및 자동 응답 워크플로우 관리")

# --- 데이터 로드 ---
try:
    users = client.get_users()
    tasks = client.get_tasks()
except Exception as e:
    st.error(f"서버 연결 오류: {e}")
    st.stop()

if not users:
    st.warning("사용자 데이터가 없습니다.")

# 데이터 매핑
user_map = {user['id']: user['name'] for user in users}
user_name_map = {user['name']: user['id'] for user in users}
user_names = list(user_name_map.keys())

# --- 필터링 ---
with c_head2:
    assignee_options = ["All Members"] + user_names
    
    query_user = st.query_params.get("user", "All Members")
    default_idx = 0
    if query_user in assignee_options:
        default_idx = assignee_options.index(query_user)
    
    selected_assignee_name = st.selectbox(
        "Filter by Assignee",
        options=assignee_options,
        index=default_idx,
    )
    
    if selected_assignee_name != query_user:
        if selected_assignee_name == "All Members":
            if "user" in st.query_params: del st.query_params["user"]
        else:
            st.query_params["user"] = selected_assignee_name
        st.rerun()

# 필터링 적용
if selected_assignee_name == "All Members":
    filtered_tasks = tasks
else:
    selected_user_id = user_name_map[selected_assignee_name]
    filtered_tasks = [task for task in tasks if task['assignee_id'] == selected_user_id]

st.markdown("---") 

# --- 칸반 보드 UI ---
col1, col2, col3 = st.columns(3, gap="medium")

tasks_todo = [t for t in filtered_tasks if t['status'] == '시작 전']
tasks_doing = [t for t in filtered_tasks if t['status'] == '진행 중']
tasks_done = [t for t in filtered_tasks if t['status'] == '완료']

def render_column(column_obj, title, tasks_list, css_class):
    with column_obj:
        st.markdown(
            f"""
            <div class="kanban-header {css_class}">
                <span>{title}</span>
                <span class="badge-count">{len(tasks_list)}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        if not tasks_list:
            st.markdown(
                f"""
                <div style="text-align:center; padding: 40px 0; color: #9CA3AF; font-size: 0.9rem; border: 2px dashed #E5E7EB; border-radius: 8px;">
                    No Tasks
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        for task in tasks_list:
            assignee = user_map.get(task['assignee_id'], 'Unassigned')
            label = f"📄 {task['title']}"
            
            with st.expander(label, expanded=False):
                draw_task_card(task, user_map, user_names, user_name_map, is_done=(title=="Done"))

# 1. To Do Column
render_column(col1, "To Do", tasks_todo, "header-todo")

# 2. In Progress Column
render_column(col2, "In Progress", tasks_doing, "header-doing")

# 3. Done Column
render_column(col3, "Done", tasks_done, "header-done")