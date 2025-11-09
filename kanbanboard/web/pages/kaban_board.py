import streamlit as st
import client
from components import draw_task_card
from typing import List, Dict, Any

st.title("할당된 업무 (칸반보드)")

try:
    users = client.get_users()
    tasks = client.get_tasks()
except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")
    st.stop() # 데이터 없이는 페이지를 그릴 수 없음

if not users:
    st.warning("사용자 정보를 불러올 수 없습니다. FastAPI 서버가 실행 중인지 확인하세요.")

if not tasks:
    st.info("현재 등록된 작업이 없습니다. AI가 이메일을 처리하면 이곳에 표시됩니다.")

# --- 데이터 매핑 ---
user_map = {user['id']: user['name'] for user in users}
user_name_map = {user['name']: user['id'] for user in users}
user_names = list(user_name_map.keys())

# --- 담당자 필터링 (st.query_params 사용) ---
assignee_options = ["전체"] + user_names
selected_name = st.query_params.get("user", "전체")

if selected_name not in assignee_options:
    selected_name = "전체"
    if "user" in st.query_params:
        del st.query_params["user"]

selected_assignee_name = st.selectbox(
    "담당자 필터:",
    options=assignee_options,
    index=assignee_options.index(selected_name),
    label_visibility="collapsed"
)

if selected_assignee_name != selected_name:
    if selected_assignee_name == "전체":
        if "user" in st.query_params: del st.query_params["user"]
    else:
        st.query_params["user"] = selected_assignee_name
    st.rerun()

if selected_assignee_name == "전체":
    filtered_tasks = tasks
else:
    selected_user_id = user_name_map[selected_assignee_name]
    filtered_tasks = [task for task in tasks if task['assignee_id'] == selected_user_id]

# --- 칸반보드 UI ---
col1, col2, col3 = st.columns(3)

tasks_todo = [t for t in filtered_tasks if t['status'] == '시작 전']
tasks_doing = [t for t in filtered_tasks if t['status'] == '진행 중']
tasks_done = [t for t in filtered_tasks if t['status'] == '완료']

# --- 1. 시작 전 ---
with col1:
    st.markdown(f'<div class="column-title title-todo">⚫️ 시작 전 ({len(tasks_todo)})</div>', unsafe_allow_html=True)
    for task in tasks_todo:
        with st.expander(f"**{task['title']}** (담당: {user_map.get(task['assignee_id'], '미지정')})"):
            draw_task_card(task, user_map, user_names, user_name_map, is_done=False)

# --- 2. 진행 중 ---
with col2:
    st.markdown(f'<div class="column-title title-doing">🔵 진행 중 ({len(tasks_doing)})</div>', unsafe_allow_html=True)
    for task in tasks_doing:
        with st.expander(f"**{task['title']}** (담당: {user_map.get(task['assignee_id'], '미지정')})"):
            draw_task_card(task, user_map, user_names, user_name_map, is_done=False)

# --- 3. 완료 ---
with col3:
    st.markdown(f'<div class="column-title title-done">🟢 완료 ({len(tasks_done)})</div>', unsafe_allow_html=True)
    for task in tasks_done:
        with st.expander(f"**{task['title']}** (담당: {user_map.get(task['assignee_id'], '미지정')})"):
            draw_task_card(task, user_map, user_names, user_name_map, is_done=False)