import streamlit as st
import requests
import os
from typing import List, Dict, Any, Optional

API_URL = os.getenv("KANBAN_SERVER_URL", "http://kanban_server:8000")

@st.cache_data(ttl=10)
def get_users() -> Optional[List[Dict[str, Any]]]:
    """모든 사용자 정보를 API에서 가져옵니다."""
    try:
        response = requests.get(f"{API_URL}/users")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"사용자 정보 로드 실패: {e}")
        return []

@st.cache_data(ttl=10)
def get_tasks() -> Optional[List[Dict[str, Any]]]:
    """모든 작업 정보를 API에서 가져옵니다."""
    try:
        response = requests.get(f"{API_URL}/tasks")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"작업 정보 로드 실패: {e}")
        return []

def update_task_api(task_id: int, task_data: Dict[str, Any]) -> bool:
    """특정 Task ID의 정보를 업데이트합니다."""
    try:
        response = requests.put(f"{API_URL}/tasks/{task_id}", json=task_data)
        response.raise_for_status()
        st.cache_data.clear()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"작업 업데이트 실패: {e} - {e.response.text if e.response else 'No response'}")
        return False

def update_user_api(user_id: int, user_data: Dict[str, Any]) -> bool:
    """특정 User ID의 정보를 업데이트합니다."""
    try:
        response = requests.put(f"{API_URL}/users/{user_id}", json=user_data)
        response.raise_for_status()
        st.cache_data.clear()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"사용자 업데이트 실패: {e} - {e.response.text if e.response else 'No response'}")
        return False

def create_user_api(user_data: Dict[str, Any]) -> bool:
    """새로운 사용자를 생성합니다."""
    try:
        response = requests.post(f"{API_URL}/users", json=user_data)
        response.raise_for_status()
        st.cache_data.clear()
        return True
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 409:
            st.error(f"사용자 생성 실패: {e.response.json().get('detail', 'Email already exists')}")
        else:
            st.error(f"사용자 생성 실패: {e} - {e.response.text if e.response else 'No response'}")
        return False