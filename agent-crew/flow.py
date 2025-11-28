import logging
import os
import json
import requests
from typing import Any
from crewai.flow.flow import Flow, start, listen, router, or_

from schemas.request_io import EmailInput, EmailFlowState
from schemas.task_output import FinalAssigneeResult

from utils.dept_registry import DepartmentRegistry
from utils.llm_helpers import determine_primary_dept, find_supporting_dept

from crews.common.filtering.crew import FilteringCrew
from crews.common.routing.crew import RoutingCrew
from crews.common.drafting.crew import DraftingCrew
from tools import send_task_to_kanban_tool, get_kanban_user_status_tool

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class SpecificLogFilter(logging.Filter):
    def filter(self, record):
        ignore_prefixes = ["http", "openai", "urllib3", "connection pool"]
        msg = record.getMessage().lower()
        return not any(msg.startswith(prefix) for prefix in ignore_prefixes)

class MemoryLogHandler(logging.Handler):
    def __init__(self, log_list):
        super().__init__()
        self.log_list = log_list
        self.formatter = logging.Formatter('%(message)s')

    def emit(self, record):
        msg = self.format(record)
        self.log_list.append(msg)

class EmailProcessingFlow(Flow[EmailFlowState]):
    default_manager = {
        "name": os.getenv("DEFAULT_MANAGER_NAME", "총괄 담당자"), 
        "email": os.getenv("DEFAULT_MANAGER_EMAIL", "manager@ajou.ac.kr")
    }
    spam_webhook_url = os.getenv("N8N_SPAM_PROCESS_WEBHOOK_URL", "")

    def __init__(self):
        super().__init__()
        self.log_handler = None

    def _setup_logger(self):
        """로그 핸들러 초기화"""
        self.state.logs = []
        self.log_handler = MemoryLogHandler(self.state.logs)
        self.log_handler.addFilter(SpecificLogFilter())
        
        root_logger = logging.getLogger()
        for h in root_logger.handlers[:]:
             if isinstance(h, MemoryLogHandler):
                 root_logger.removeHandler(h)
        
        root_logger.addHandler(self.log_handler)
        logging.getLogger("crewai").addHandler(self.log_handler)

    def _cleanup_logger(self):
        """로그 핸들러 정리"""
        if self.log_handler:
            logging.getLogger().removeHandler(self.log_handler)
            logging.getLogger("crewai").removeHandler(self.log_handler)

    # --- [Log Callbacks] ---
    def _log_crew_step(self, step: Any):
        if hasattr(step, 'thought') and step.thought:
            clean_thought = step.thought.replace("Thought:", "").strip()
            logger.info(f"// {clean_thought}")
        
        if hasattr(step, 'tool') and step.tool:
            logger.info(f"$ Using tool: {step.tool}")

    def _log_task_finish(self, output: Any):
        agent_name = getattr(output, 'agent', 'Unknown Agent')
        logger.info(f"[OUTPUT] ✅ Task Completed by: {agent_name}")

    @start()
    def start_flow(self):
        self._setup_logger()
        logger.info("[SYSTEM] 🚀 Flow Started")
        
        self.state.email_data = getattr(self, "_email_input", None)
        self.state.retry_count = 0
        self.state.current_context = ""
        self.state.draft_status = "PENDING"
        
        return self.state.email_data

    # --- STEP 1: 분류 (Filtering) ---
    @listen(start_flow)
    def classify_email(self, email_data: EmailInput):
        logger.info(">> STEP 1: Classification")
        try:
            crew = FilteringCrew().crew()
            crew.step_callback = self._log_crew_step
            crew.task_callback = self._log_task_finish
            
            result = crew.kickoff(inputs=email_data.dict()).pydantic
            self.state.analysis_result = result
            logger.info(f"[SYSTEM] Category: {result.category}")
            return result.category
        except Exception as e:
            logger.error(f"Classification Error: {e}")
            return "OTHER"

    @router(classify_email)
    def route_by_category(self, category: str):
        if category == "TASK": 
            return "SELECT_DEPT"
        elif category == "Simple_Inquiry": 
            return "SIMPLE_INQUIRY"
        else:
            return "SPAM_HANDLER"

    # --- STEP 2: 부서 선정 (Dept Selection) ---
    @listen("SELECT_DEPT")
    def select_primary_dept(self):
        logger.info(">> STEP 2: Selecting Primary Dept")
        email_body = self.state.email_data.body
        
        decision = determine_primary_dept(email_body)
        self.state.routing_decision = decision.model_dump()
        
        if decision.is_spam:
            logger.info(">> Classified as SPAM by Router.")
            return "SPAM_HANDLER"
        
        return "ASSIGN_STAFF"

    @router(select_primary_dept)
    def route_after_dept_selection(self, next_step: str):
        return next_step

    # --- STEP 3: 담당자 배정 (Assign Staff) ---
    @listen("ASSIGN_STAFF")
    def assign_staff(self):
        primary_id = self.state.routing_decision.get("primary_dept_id")
        logger.info(f">> STEP 3: Assigning Staff (Dept: {primary_id})")
        
        email_body = self.state.email_data.body
        summary = self.state.analysis_result.summary
        
        try:
            crew = RoutingCrew().crew()
            crew.step_callback = self._log_crew_step
            crew.task_callback = self._log_task_finish
            
            routing_res = crew.kickoff(inputs={
                "email_summary": f"[{primary_id}] {summary}",
                "body": email_body
            }).pydantic
            
            # 3-1. 스케줄 확인 및 최종 배정
            status_json = get_kanban_user_status_tool._run(assignee_email=routing_res.recipient_email)
            try:
                parsed = json.loads(status_json)
                if isinstance(parsed, list): parsed = parsed[0] if parsed else {}
                status = parsed.get('status', 'Unknown')
            except:
                status = 'Unknown'
            
            final_email = routing_res.recipient_email
            final_name = routing_res.recipient_name
            
            if status != 'Available':
                logger.warning(f"Assignee {final_name} unavailable ({status}). Fallback to Manager.")
                final_email = self.default_manager["email"]
                final_name = self.default_manager["name"]
            
            self.state.final_assignee_result = FinalAssigneeResult(
                final_assignee_name=final_name, 
                final_assignee_email=final_email,
                status="Success", 
                reasoning=f"Dept: {primary_id}, Staff: {final_name}"
            )
            
            
        except Exception as e:
            logger.exception(f"Routing Failed: {e}")
            self.state.final_assignee_result = FinalAssigneeResult(
                final_assignee_name=self.default_manager["name"], 
                final_assignee_email=self.default_manager["email"],
                status="Failed", 
                reasoning=f"Error: {e}"
            )
        finally:
            # 첫 루프를 위한 타겟 설정 (주관 부서)
            self.state.target_dept_id = primary_id
            self.state.search_query = email_body

    # --- STEP 4: 정보 수집 (Retrieval Loop) ---
    @listen(or_(assign_staff, "RETRIEVE_INFO"))
    def retrieve_info(self):
        target_id = self.state.target_dept_id
        query = self.state.search_query
        attempt = self.state.retry_count
        
        log_prefix = "Initial" if attempt == 0 else f"Additional (Attempt {attempt})"
        logger.info(f">> STEP 4: {log_prefix} Retrieval from [{target_id}]")
        
        crew_cls = DepartmentRegistry.get_crew(target_id)
        new_info = ""
        
        if crew_cls:
            try:
                dept_crew = crew_cls()
                info = dept_crew.get_information(
                    query=query,
                    step_callback=self._log_crew_step,
                    task_callback=self._log_task_finish
                )
                new_info = f"\n[출처: {target_id}] {info}\n"
            except Exception as e:
                logger.error(f"Retrieval error from {target_id}: {e}")
                new_info = f"\n[System] {target_id} 정보 수집 실패: {e}\n"
        else:
            logger.warning(f"Department {target_id} not found.")
            new_info = f"\n[System] 부서 ID '{target_id}'를 찾을 수 없습니다.\n"
            
        # 컨텍스트 누적
        self.state.current_context += new_info

    # --- STEP 5: 초안 작성 (Drafting) ---
    @listen(retrieve_info)
    def draft_email(self):
        logger.info(f">> STEP 5: Drafting Email (Retry: {self.state.retry_count})")
        
        primary_id = self.state.routing_decision.get("primary_dept_id")
        dept_persona = DepartmentRegistry.get_persona(primary_id)
        
        try:
            crew = DraftingCrew().crew()
            crew.step_callback = self._log_crew_step
            crew.task_callback = self._log_task_finish
            
            draft_res = crew.kickoff(inputs={
                "email_body": self.state.email_data.body,
                "retrieved_context": self.state.current_context,
                "dept_persona": dept_persona
            })
            
            output = draft_res.pydantic
            if not output:
                raise ValueError("Drafting output parsing failed.")

            self.state.draft_status = output.status
            
            if output.status == "COMPLETED":
                # 성공 시 칸반보드 업로드
                self._send_kanban(output.draft_content)
                return "COMPLETED"
            
            elif output.status == "NEEDS_INFO":
                # 정보 부족 시 쿼리와 힌트 임시 저장 (Router에서 처리)
                logger.warning(f"   >> Missing Info: {output.missing_info_query}")
                self.state.search_query = output.missing_info_query # 다음 검색 쿼리로 설정
                self._temp_hint = output.target_dept_hint
                return "NEEDS_INFO"
                
        except Exception as e:
            logger.exception(f"Drafting Failed: {e}")
            self._send_kanban(f"초안 작성 중 오류가 발생했습니다: {e}")
            return "ERROR"

    # --- STEP 6: 판단 및 라우팅 (Router) ---
    @router(draft_email)
    def evaluate_draft(self, status: str):
        if status == "COMPLETED" or status == "ERROR":
            return "FINISH"
            
        if status == "NEEDS_INFO":
            # 재시도 횟수 제한 (예: 최대 3회)
            if self.state.retry_count >= 3:
                return "FORCE_FINALIZE"
            
            # 다음 부서 찾기
            logger.info("   >> Identifying Supporting Department...")
            target_dept = find_supporting_dept(self.state.search_query, self._temp_hint)
            
            if target_dept:
                self.state.target_dept_id = target_dept
                self.state.retry_count += 1
                return "RETRIEVE_INFO" # 루프: 다시 정보 수집 단계로
            else:
                logger.warning("   >> Could not find supporting dept.")
                # 부서를 못 찾으면 그냥 현재 상태로 강제 종료 혹은 매니저에게 넘김
                return "FORCE_FINALIZE"
        
        return "FINISH"

    # --- 종료 및 예외 처리 핸들러 ---
    
    @listen("FORCE_FINALIZE")
    def force_finalize(self):
        logger.warning(">> Max retries reached or Dept not found. Sending incomplete.")
        self._send_kanban(
            "죄송합니다. 내부 정보를 확인하는 데 시간이 소요되고 있습니다. \n"
            "담당자가 내용을 확인 후 신속히 다시 연락드리겠습니다.\n\n"
            f"(확인된 정보: {self.state.current_context[:200]}...)"
        )
        return "FINISH"

    @listen("FINISH")
    def finish_flow(self):
        logger.info("[SYSTEM] ✅ Flow Finished.")

    # --- 별도 경로: 단순 문의 (Simple Inquiry) ---
    @listen("SIMPLE_INQUIRY")
    def handle_simple(self):
        logger.info(">> Handling Simple Inquiry")
        email_data = self.state.email_data
        dept_persona = "친절한 대학 행정 안내 데스크"
        context = "이 문의는 단순 정보 요청입니다. 친절하게 확인 후 회신드리겠다고 답변하세요."
        
        try:
            crew = DraftingCrew().crew()
            crew.step_callback = self._log_crew_step
            crew.task_callback = self._log_task_finish
            
            draft_res = crew.kickoff(inputs={
                "email_body": email_data.body,
                "retrieved_context": context,
                "dept_persona": dept_persona
            })
            
            final_draft = draft_res.pydantic.draft_content if draft_res.pydantic else str(draft_res.raw)
            
            self.state.final_assignee_result = FinalAssigneeResult(
                final_assignee_name=self.default_manager["name"], 
                final_assignee_email=self.default_manager["email"],
                status="Simple", reasoning="Simple Inquiry"
            )
            self._send_kanban(final_draft)
        except Exception as e:
            logger.error(f"Simple Handle Error: {e}")
            self._send_kanban("담당자가 확인 후 연락드리겠습니다.")

    # --- 별도 경로: 스팸 처리 (Spam) ---
    @listen("SPAM_HANDLER")
    def handle_spam(self):
        logger.info("[ROUTE] Handling SPAM/Irrelevant")
        self._cleanup_logger()
        try:
            if self.spam_webhook_url:
                payload = {"message_id": self.state.email_data.message_id}
                requests.post(self.spam_webhook_url, json=payload)
                logger.info("[SYSTEM] Spam Webhook sent.")
            else:
                logger.info("[SYSTEM] No Spam Webhook URL defined.")
        except Exception as e:
            logger.error(f"[ERROR] Spam Webhook failed: {e}")

    # --- 공통 유틸리티 ---
    def _send_kanban(self, draft):
        """최종 결과를 칸반 보드로 전송"""
        self._cleanup_logger()
        
        assignee = self.state.final_assignee_result
        if not assignee:
             assignee = FinalAssigneeResult(
                final_assignee_name=self.default_manager["name"], 
                final_assignee_email=self.default_manager["email"],
                status="Fallback", reasoning="Logic Error"
            )
        
        email = self.state.email_data
        full_logs = "\n".join(self.state.logs)
        
        try:
            send_task_to_kanban_tool._run(
                message_id=email.message_id, 
                sender=email.sender, 
                subject=email.subject, 
                body=email.body,
                final_draft=draft, 
                assignee_name=assignee.final_assignee_name, 
                assignee_email=assignee.final_assignee_email,
                execution_logs=full_logs
            )
            logger.info("[SYSTEM] Task sent to Kanban successfully.")
        except Exception as e:
            logger.error(f"[SYSTEM] Failed to send to Kanban: {e}")