# user_management.py

import streamlit as st
import pandas as pd
import client
from typing import Dict, Any
from components import apply_custom_styles, metric_card

# --- 페이지 설정 및 스타일 적용 ---
st.set_page_config(page_title="User Management", layout="wide")
apply_custom_styles()

# --- 헤더 영역 ---
st.title("Team Members")
st.markdown(
    """
    <div style="color: #6B7280; margin-bottom: 20px;">
    팀원들의 상태와 정보를 관리합니다. 상태 변경 후 반드시 <b>'저장'</b> 버튼을 눌러주세요.
    </div>
    """, 
    unsafe_allow_html=True
)

# --- 데이터 로드 ---
try:
    users = client.get_users()
except Exception as e:
    st.error(f"서버 연결 실패: {e}")
    st.stop()

if not users:
    st.warning("사용자 데이터가 없습니다.")
    st.stop()

users_df = pd.DataFrame(users)
if 'tasks' in users_df.columns:
    users_df = users_df.drop(columns=['tasks'])

# --- KPI 요약 정보 (상단) ---
total_users = len(users_df)
active_users = len(users_df[users_df['status'] == '업무 중'])
vacation_users = len(users_df[users_df['status'] == '휴가 중'])

col_m1, col_m2, col_m3, col_spacer = st.columns([1, 1, 1, 3])
with col_m1:
    metric_card("Total Members", f"{total_users}명", "👥")
with col_m2:
    metric_card("Working Now", f"{active_users}명", "🔥")
with col_m3:
    metric_card("On Vacation", f"{vacation_users}명", "vacation")

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# --- 메인 콘텐츠 (데이터 그리드) ---
with st.container():
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    
    c1, c2 = st.columns([4, 1])
    with c1:
        st.subheader("Member List")
    with c2:
        save_btn = st.button("💾 변경 사항 저장", type="primary", use_container_width=True)

    disabled_columns = ["id", "email"]

    edited_df = st.data_editor(
        users_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "id": st.column_config.NumberColumn(
                "ID", 
                help="고유 식별자", 
                width="small",
                disabled=True
            ),
            "name": st.column_config.TextColumn(
                "Name", 
                width="medium",
                required=True,
                validate="^[가-힣a-zA-Z]+$"
            ),
            "email": st.column_config.TextColumn(
                "Email Address", 
                width="large",
                disabled=True
            ),
            "department": st.column_config.TextColumn(
                "Department", 
                width="medium"
            ),
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["업무 중", "휴가 중", "출장 중", "회의 중"],
                width="medium",
                required=True,
                help="현재 업무 상태를 선택하세요"
            )
        },
        disabled=disabled_columns
    )
    st.markdown('</div>', unsafe_allow_html=True)

# --- 저장 로직 ---
if save_btn:
    edited_users = edited_df.to_dict('records')
    original_users_dict = {u['id']: u for u in users}
    
    updated_count = 0
    failed_count = 0
    
    with st.spinner("동기화 중..."):
        for edited_user in edited_users:
            if 'id' not in edited_user or pd.isna(edited_user['id']):
                continue 
            
            original_user = original_users_dict.get(edited_user['id'])
            
            if original_user and original_user != edited_user:
                update_payload: Dict[str, Any] = edited_user.copy()
                del update_payload['id'] 
                
                if client.update_user_api(edited_user['id'], update_payload):
                    updated_count += 1
                else:
                    failed_count += 1
    
    if failed_count > 0: 
        st.toast(f"{failed_count}건 업데이트 실패", icon="⚠️")
    if updated_count > 0: 
        st.balloons()
        st.toast(f"{updated_count}명의 정보가 업데이트 되었습니다!", icon="✅")
        st.rerun()
    if updated_count == 0 and failed_count == 0: 
        st.info("변경된 내용이 없습니다.")