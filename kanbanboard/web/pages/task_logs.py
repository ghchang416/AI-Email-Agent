import streamlit as st
import client
import re
import html
import textwrap
from components import apply_custom_styles

def strip_tags(text: str) -> str:
    """간단한 HTML 태그 제거기"""
    if not text:
        return ""
    text = str(text)
    return re.sub(r"<[^>]*>", "", text)

# --- 페이지 설정 ---
st.set_page_config(page_title="System Logs", page_icon="📟", layout="wide")
apply_custom_styles()

# --- CSS: Developer Console Style ---
st.markdown("""
<style>
    body, .stApp { 
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
        background-color: #F9FAFB;
    }

    /* --- List View Styles --- */
    .task-row {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: box-shadow 0.2s ease;
    }
    .task-row:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-color: #D1D5DB;
    }
    .task-meta {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .task-id {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #6B7280;
    }
    .task-title {
        font-weight: 600;
        color: #111827;
        font-size: 1rem;
    }
    .status-badge {
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 999px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .status-done { background: #ECFDF5; color: #059669; }
    .status-prog { background: #EFF6FF; color: #2563EB; }
    .status-todo { background: #F3F4F6; color: #4B5563; }

    /* --- Detail View Styles --- */
    
    /* Left Panel: Meta Card */
    .meta-panel {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .meta-label {
        font-size: 0.75rem;
        color: #6B7280;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 5px;
        margin-top: 15px;
    }
    .meta-label:first-child { margin-top: 0; }
    .meta-value {
        font-size: 0.9rem;
        color: #111827;
        font-weight: 500;
        word-break: break-all;
    }
    
    /* Email Body Box */
    .email-box {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 15px;
        font-size: 0.9rem;
        color: #374151;
        line-height: 1.6;
        white-space: pre-wrap; /* 줄바꿈 유지 */
        margin-top: 10px;
    }

    /* Right Panel: Terminal Console */
    .console-window {
        background-color: #1E1E1E; /* VS Code Dark */
        border-radius: 8px;
        border: 1px solid #333;
        padding: 0;
        overflow: hidden;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        margin-bottom: 30px;
    }
    .console-header {
        background-color: #252526;
        padding: 8px 16px;
        border-bottom: 1px solid #333;
        display: flex;
        gap: 6px;
        align-items: center;
    }
    .dot { width: 10px; height: 10px; border-radius: 50%; }
    .dot-red { background: #FF5F56; }
    .dot-yellow { background: #FFBD2E; }
    .dot-green { background: #27C93F; }
    .console-title { color: #9CA3AF; font-size: 0.8rem; margin-left: 10px; }

    .console-body {
        padding: 20px;
        color: #D4D4D4;
        font-size: 0.85rem;
        line-height: 1.6;
        min-height: 400px;
        max-height: 800px;
        overflow-y: auto;
    }

    /* Log Line Styling */
    .log-line { margin-bottom: 6px; }
    
    .log-thought { color: #6A9955; font-style: italic; } /* Comment Green */
    .log-tool { color: #569CD6; font-weight: bold; } /* Keyword Blue */
    .log-system { color: #C586C0; font-weight: bold; } /* Control Flow Purple */
    .log-output { color: #CE9178; } /* String Orange */
    .log-error { color: #F48771; } /* Red */
    .log-header { 
        color: #4EC9B0; /* Type Green/Blue */
        font-weight: bold; 
        margin-top: 20px; 
        margin-bottom: 10px; 
        border-bottom: 1px solid #3E3E42;
        padding-bottom: 5px;
    }

    /* Action Button */
    .action-btn {
        text-decoration: none;
        color: #4B5563;
        font-size: 0.9rem;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .action-btn:hover { color: #111827; }

</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def parse_logs(log_text):
    if not log_text: return []
    lines = log_text.split('\n')
    parsed = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        entry = {"type": "normal", "content": line}
        
        if ">> STEP" in line:
            entry["type"] = "header"
        elif "[THOUGHT]" in line:
            entry["type"] = "thought"
            entry["content"] = line.replace("[THOUGHT]", "").strip()
            entry["content"] = f"// {entry['content']}" 
        elif "[TOOL]" in line:
            entry["type"] = "tool"
            entry["content"] = line.replace("[TOOL]", "").strip()
            entry["content"] = f"$ {entry['content']}" 
        elif "[OUTPUT]" in line or "[SYSTEM]" in line:
            entry["type"] = "system"
        elif "[ERROR]" in line:
            entry["type"] = "error"
        elif "[WARNING]" in line:
            entry["type"] = "error"
            
        parsed.append(entry)
    return parsed

# --- Main Logic ---

try:
    tasks = client.get_tasks()
    tasks.sort(key=lambda x: x['id'], reverse=True)
except:
    tasks = []

task_id = st.query_params.get("task_id", None)

if not task_id:
    # === List View ===
    st.title("System Logs")
    st.markdown("<div style='color:#6B7280; margin-bottom:20px;'>Monitor AI agent execution traces and debugging info.</div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns([0.5, 4, 1.5, 1])
    c1.markdown("**ID**")
    c2.markdown("**Subject**")
    c3.markdown("**Status**")
    c4.markdown("") 
    
    st.divider()

    for task in tasks:
        status = task['status']
        s_class = "status-todo"
        if status == "완료": s_class = "status-done"
        elif status == "진행 중": s_class = "status-prog"
        
        with st.container():
            c1, c2, c3, c4 = st.columns([0.5, 4, 1.5, 1])
            c1.caption(f"#{task['id']}")
            with c2:
                st.markdown(f"<div class='task-title'>{task['title']}</div>", unsafe_allow_html=True)
                st.caption(f"{task.get('sender_email', 'Unknown')} • {task['message_id']}")
            with c3:
                st.markdown(f"<span class='status-badge {s_class}'>{status}</span>", unsafe_allow_html=True)
            with c4:
                if st.button("Inspect", key=f"btn_{task['id']}", use_container_width=True):
                    st.query_params["task_id"] = str(task['id'])
                    st.rerun()
            st.markdown("<hr style='margin:10px 0; border-color:#F3F4F6;'>", unsafe_allow_html=True)

else:
    # === Detail Console View ===
    current_task = next((t for t in tasks if str(t['id']) == task_id), None)
    
    if not current_task:
        st.error("Task not found.")
        if st.button("Back"):
            st.query_params.clear()
            st.rerun()
        st.stop()

    if st.button("← Back to Logs"):
        st.query_params.clear()
        st.rerun()

    st.markdown(f"### Execution Trace #{current_task['id']}")
    
    col_left, col_right = st.columns([1, 2.5], gap="medium")
    
    with col_left:
        # 원본 값 가져오기
        raw_subject = current_task.get('title', '')
        raw_status = current_task.get('status', '')
        raw_sender_name = current_task.get('sender_name', '')
        raw_sender_email = current_task.get('sender_email', '')
        raw_body = current_task.get('received_mail_content', 'No content available.')

        # 태그 제거 + escape
        subject = html.escape(strip_tags(raw_subject))
        status = html.escape(strip_tags(raw_status))
        sender_name = html.escape(strip_tags(raw_sender_name))
        sender_email = html.escape(strip_tags(raw_sender_email))

        # 이메일 본문 처리
        safe_body = html.escape(strip_tags(raw_body))
        safe_body = safe_body.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")

        # 메타 패널 HTML (textwrap 없이 직접 문자열)
        meta_html = (
            "<style>"
            ".meta-panel { background:#F9FAFB; border:1px solid #E5E7EB; padding:16px 20px; "
            "border-radius:10px; margin-bottom:20px; }"
            ".meta-row { margin-bottom:12px; }"
            ".meta-label { font-size:0.85rem; font-weight:600; color:#6B7280; margin-bottom:4px; }"
            ".meta-value { font-size:1rem; color:#111827; font-weight:500; word-break:break-word; }"
            ".meta-value-small { font-size:0.82rem; color:#6B7280; margin-top:4px; }"
            ".email-box { background:#ffffff; border:1px solid #E5E7EB; padding:12px; "
            "border-radius:8px; white-space:normal; word-break:break-word; }"
            "</style>"

            "<div class='meta-panel'>"

                "<div class='meta-row'>"
                    "<div class='meta-label'>Subject</div>"
                    f"<div class='meta-value'>{subject}</div>"
                "</div>"

                "<div class='meta-row'>"
                    "<div class='meta-label'>Status</div>"
                    f"<div class='meta-value'>{status}</div>"
                "</div>"

                "<div class='meta-row'>"
                    "<div class='meta-label'>Sender</div>"
                    f"<div class='meta-value'>{sender_name}</div>"
                    f"<div class='meta-value-small'>{sender_email}</div>"
                "</div>"

            "</div>"
        )

        st.markdown(meta_html, unsafe_allow_html=True)

        st.markdown("**Original Email Body**")
        email_html = f"<div class='email-box'>{safe_body}</div>"
        st.markdown(email_html, unsafe_allow_html=True)
        
    # --- Right Panel: Console ---
    with col_right:
        logs = parse_logs(current_task.get('execution_logs', ''))
        
        console_html = """
        <div class="console-window">
            <div class="console-header">
                <div class="dot dot-red"></div>
                <div class="dot dot-yellow"></div>
                <div class="dot dot-green"></div>
                <div class="console-title">crewai-agent — trace.log</div>
            </div>
            <div class="console-body">
        """
        
        if not logs:
             console_html += '<div class="log-line" style="color:#666;">> No execution logs found.</div>'
        else:
            console_html += '<div class="log-line" style="color:#666; margin-bottom:15px;">> Initializing log viewer...</div>'
            
            for log in logs:
                css_class = f"log-{log['type']}"
                content = html.escape(log['content'])
                
                if log['type'] == 'header':
                    console_html += f'<div class="log-header">{content}</div>'
                else:
                    style = "padding-left: 15px;" if log['type'] == 'thought' else ""
                    console_html += f'<div class="log-line {css_class}" style="{style}">{content}</div>'
            
            console_html += '<div class="log-line" style="color:#4EC9B0; margin-top:20px;">> End of stream_</div>'

        console_html += """
            </div>
        </div>
        """
        st.markdown(console_html, unsafe_allow_html=True)