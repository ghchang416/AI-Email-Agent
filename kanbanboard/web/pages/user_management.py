import streamlit as st
import pandas as pd
import client
from typing import Dict, Any

st.title("👩‍💼 사용자 관리")
st.markdown("테이블에서 직접 사용자의 상태(휴가, 바쁨 등)를 변경할 수 있습니다. 변경 사항은 '저장' 버튼을 눌러야 API에 반영됩니다.")

try:
    users = client.get_users()
except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")
    st.stop()

if not users:
    st.warning("사용자 정보를 불러올 수 없습니다. FastAPI 서버가 실행 중인지 확인하세요.")

# --- 데이터 에디터 (st.data_editor) ---
users_df = pd.DataFrame(users)
if 'tasks' in users_df.columns:
    users_df = users_df.drop(columns=['tasks'])

disabled_columns = ["id", "email"]

edited_df = st.data_editor(
    users_df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "id": st.column_config.NumberColumn("ID (고유값)", disabled=True),
        "name": st.column_config.TextColumn("이름", required=True),
        "email": st.column_config.TextColumn("이메일", disabled=True),
        "department": st.column_config.TextColumn("소속"),
        "status": st.column_config.SelectboxColumn(
            "상태",
            options=["업무 중", "휴가 중"], 
            required=True,
        )
    },
    disabled=disabled_columns
)

# --- 변경 사항 저장 로직 ---
if st.button("변경 사항 저장", type="primary"):
    edited_users = edited_df.to_dict('records')
    original_users_dict = {u['id']: u for u in users}
    
    updated_count = 0
    failed_count = 0
    
    with st.spinner("변경 사항을 저장 중입니다..."):
        for edited_user in edited_users:
            if 'id' not in edited_user or pd.isna(edited_user['id']):
                # TODO: 
                continue 
            
            original_user = original_users_dict.get(edited_user['id'])
            
            # 원본과 비교하여 변경된 사항이 있을 때만 API 호출
            if original_user and original_user != edited_user:
                update_payload: Dict[str, Any] = edited_user.copy()
                del update_payload['id'] 
                
                if client.update_user_api(edited_user['id'], update_payload):
                    updated_count += 1
                else:
                    failed_count += 1
    
    if failed_count > 0: st.error(f"{failed_count}건의 사용자 정보 업데이트에 실패했습니다.")
    if updated_count > 0: st.success(f"{updated_count}건의 사용자 정보가 성공적으로 업데이트되었습니다."); st.rerun()
    if updated_count == 0 and failed_count == 0: st.info("변경 사항이 없습니다.")