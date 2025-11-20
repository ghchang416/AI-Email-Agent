import requests
import logging
import os
import json
from typing import Tuple, Optional, Any
from crewai.flow.flow import Flow, start, listen, router
from crews.filtering.crew import FilteringCrew
from crews.drafting.crew import DraftingCrew
from crews.routing.crew import RoutingCrew
from schemas.request_io import EmailInput, EmailFlowState
from schemas.task_output import DraftValidation, EmailAnalysis, FinalAssigneeResult
from tools import send_task_to_kanban_tool

logger = logging.getLogger(__name__)

# 노이즈 필터링
class SpecificLogFilter(logging.Filter):
    def filter(self, record):
        ignore_prefixes = ["http", "openai", "urllib3", "connection pool"]
        msg = record.getMessage().lower()
        return not any(msg.startswith(prefix) for prefix in ignore_prefixes)

# 메모리 로그 핸들러
class MemoryLogHandler(logging.Handler):
    def __init__(self, log_list):
        super().__init__()
        self.log_list = log_list
        self.formatter = logging.Formatter('%(message)s')

    def emit(self, record):
        msg = self.format(record)
        self.log_list.append(msg)

class EmailProcessingFlow(Flow[EmailFlowState]):
    MAX_RETRIES = 1
    MAX_ROUTING_ATTEMPTS = 3
    spam_webhook_url = os.getenv("N8N_SPAM_PROCESS_WEBHOOK_URL", "http://n8n:5678/webhook/3228da63-16c5-44d8-9852-dab75bdb24c0")
    default_name = os.getenv("DEFAULT_MANAGER_NAME", "총괄 담당자")
    default_email = os.getenv("DEFAULT_MANAGER_EMAIL", "manager@ajou.ac.kr")

    def _log_crew_step(self, step: Any):
        """[Step Callback] 에이전트의 생각(Thought)과 도구 호출(Tool Call)만 기록"""
        # Thought
        if hasattr(step, 'thought') and step.thought:
            clean_thought = step.thought.replace("Thought:", "").strip()
            logger.info(f"[THOUGHT] {clean_thought}")
        
        # Tool Call (입력값은 생략하고 도구 이름만)
        if hasattr(step, 'tool') and step.tool:
            logger.info(f"[TOOL] Using tool: {step.tool}")

    def _log_task_finish(self, output: Any):
        """[Task Callback] 태스크 완료 시 에이전트 이름과 최종 결과(Pydantic) 기록"""
        agent_name = getattr(output, 'agent', 'Unknown Agent')
        
        logger.info(f"\n[OUTPUT] ✅ Task Completed by: {agent_name}")
        
        # Pydantic 출력 확인 (구조화된 데이터)
        if hasattr(output, 'pydantic') and output.pydantic:
            try:
                model_str = str(output.pydantic)
                logger.info(f"[DATA] Structured Result:\n{model_str}")
            except:
                logger.info(f"[DATA] Result: {output.pydantic}")
        
        # 일반 텍스트 결과 (너무 길면 요약)
        elif hasattr(output, 'raw'):
            clean_raw = output.raw.strip()
            if len(clean_raw) > 200:
                logger.info(f"[RESULT] {clean_raw[:200]}... (truncated)")
            else:
                logger.info(f"[RESULT] {clean_raw}")

    @start()
    def start_flow(self):
        self.state.logs = []
        self.log_handler = MemoryLogHandler(self.state.logs)
        self.log_handler.addFilter(SpecificLogFilter())
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        for h in root_logger.handlers[:]:
             if isinstance(h, MemoryLogHandler):
                 root_logger.removeHandler(h)
        root_logger.addHandler(self.log_handler)
        logging.getLogger("crewai").addHandler(self.log_handler)

        logger.info("[SYSTEM] 🚀 Workflow Initialized")
        logger.info(f"[INFO] Processing Email ID: {getattr(self, '_email_input', None).message_id}")
        
        email = getattr(self, "_email_input", None)
        self.state.email_data = email
        return email

    @listen(start_flow)
    def run_filtering(self, email_data: EmailInput) -> EmailAnalysis:
        logger.info("\n>> STEP 1: Filtering & Analysis")
        
        inputs = {
            "sender": email_data.sender,
            "subject": email_data.subject,
            "body": email_data.body
        }
        
        crew = FilteringCrew().crew()
        crew.step_callback = self._log_crew_step
        crew.task_callback = self._log_task_finish
        
        result = crew.kickoff(inputs=inputs).pydantic
        
        self.state.analysis_result = result
        logger.info(f"[SYSTEM] Flow Category: {result.category}")
        return result
    
    @router(run_filtering) 
    def route_email(self, analysis: EmailAnalysis) -> str:
        return analysis.category

    @listen("OTHER")
    def handle_other(self):
        logger.info("[ROUTE] Handling 'OTHER' (Spam/Irrelevant)")
        try:
            payload = {"message_id": self.state.email_data.message_id}
            requests.post(self.spam_webhook_url, json=payload)
            logger.info("[SYSTEM] Webhook sent.")
        except Exception as e:
            logger.error(f"[ERROR] Webhook failed: {e}")
        return "Flow finished for OTHER."

    @listen("TASK")
    def handle_task(self) -> Tuple[str, Optional[str]]:
        logger.info("\n>> STEP 2: Routing Agent (Task Assignment)")
        
        email_summary = self.state.analysis_result.summary
        email_data = self.state.email_data
        excluded_assignees_list = [] 
        self.state.final_assignee_result = None
        
        routing_succeeded = False

        for attempt in range(self.MAX_ROUTING_ATTEMPTS):
            logger.info(f"\n[INFO] Routing Attempt {attempt + 1}/{self.MAX_ROUTING_ATTEMPTS}")

            routing_inputs = {
                "sender": email_data.sender,
                "subject": email_data.subject,
                "body": email_data.body,
                "email_summary": email_summary,
                "excluded_assignees_list": excluded_assignees_list
            }

            try:
                crew = RoutingCrew().crew()
                crew.step_callback = self._log_crew_step
                crew.task_callback = self._log_task_finish
                
                final_result = crew.kickoff(inputs=routing_inputs).pydantic

                if not final_result: 
                    logger.warning("[WARNING] Empty result from RoutingCrew.")
                    continue 
                
                if final_result.status == 'Success':
                    logger.info(f"[SYSTEM] Routing Success: {final_result.final_assignee_name}")
                    self.state.final_assignee_result = final_result
                    routing_succeeded = True
                    break
                else:
                    logger.warning(f"[WARNING] Routing Failed: {final_result.reasoning}")
                    excluded_assignees_list.append(final_result.final_assignee_email)
            
            except Exception as e:
                logger.error(f"[ERROR] Routing Exception: {e}")
        
        if not routing_succeeded:
            logger.warning("[INFO] Fallback to Default Manager")
            self.state.final_assignee_result = FinalAssigneeResult(
                final_assignee_name=self.default_name,
                final_assignee_email=self.default_email,
                status="Success",
                reasoning="Fallback"
            )

        return self._run_drafting_crew()
    
    @listen("Simple_Inquiry")
    def handle_inquiry(self) -> Optional[str]:
        logger.info("\n>> STEP 2: Drafting Agent (Simple Inquiry)")
        return self._run_drafting_crew()

    def _run_drafting_crew(self) -> Optional[str]:
        final_draft = None
        validation_passed = False
        attempts = 0
        
        inputs_for_crew = {
            "email_summary": self.state.analysis_result.summary,
            "email_body": self.state.email_data.body,
            "category": self.state.analysis_result.category
        }
        
        while not validation_passed and attempts < self.MAX_RETRIES:
            attempts += 1
            logger.info(f"\n[INFO] Drafting Iteration {attempts}")
            
            crew = DraftingCrew().crew()
            crew.step_callback = self._log_crew_step
            crew.task_callback = self._log_task_finish
            
            crew_result = crew.kickoff(inputs=inputs_for_crew)
            
            try:
                if crew_result.tasks_output and len(crew_result.tasks_output) > 0:
                    draft_candidate = str(crew_result.tasks_output[0].raw)
                else:
                    draft_candidate = str(crew_result.raw)
                
                validation = crew_result.pydantic
                
                if validation and validation.passed:
                    validation_passed = True
                    final_draft = draft_candidate
                    logger.info("[SYSTEM] Draft Approved.")
                else:
                    critique = validation.critique if validation else "Parsing Failed"
                    logger.warning(f"[SYSTEM] Draft Rejected: {critique}")
                    inputs_for_crew['last_critique'] = critique
                    
            except Exception as e:
                logger.error(f"[ERROR] Output parsing error: {e}")
                final_draft = str(crew_result.raw)
        
        return final_draft

    @listen(handle_task)
    def handle_task_post_action(self, final_draft: Optional[str]):
        self._cleanup_logger()
        full_log_text = "\n".join(self.state.logs)
        
        logger.info("\n>> STEP 3: Finalizing Task")
        
        try:
            email_data = self.state.email_data
            assignee_data = self.state.final_assignee_result

            success = send_task_to_kanban_tool._run(
                message_id=email_data.message_id,
                sender=email_data.sender,
                subject=email_data.subject,
                body=email_data.body,
                final_draft=final_draft,
                assignee_name=assignee_data.final_assignee_name,
                assignee_email=assignee_data.final_assignee_email,
                execution_logs=full_log_text
            )
            logger.info(f"[SYSTEM] Upload to Kanban: {'Success' if success else 'Failed'}")
            return "Success" if success else "Failed"
        except Exception as e:
            logger.error(f"[ERROR] {e}")
            return "Error"
        
    @listen(handle_inquiry)
    def handle_inquiry_post_action(self, final_draft: Optional[str]):
        self._cleanup_logger()
        full_log_text = "\n".join(self.state.logs)

        logger.info("\n>> STEP 3: Auto-Reply Execution")

        if final_draft:
            try:
                email_data = self.state.email_data
                success = send_task_to_kanban_tool._run(
                    message_id=email_data.message_id,
                    sender=email_data.sender,
                    subject=email_data.subject,
                    body=email_data.body,
                    final_draft=final_draft,
                    assignee_name=self.default_name, 
                    assignee_email=self.default_email,
                    execution_logs=full_log_text,
                    auto_reply=True
                )
                logger.info(f"[SYSTEM] Auto-Reply Result: {'Success' if success else 'Failed'}")
                return "Auto_Handled" if success else "Failed"
            except Exception:
                return "Error"
        else:
            logger.warning("[SYSTEM] Draft failed. Creating fallback task.")
            try:
                email_data = self.state.email_data
                send_task_to_kanban_tool._run(
                    message_id=email_data.message_id,
                    sender=email_data.sender,
                    subject=email_data.subject,
                    body=email_data.body,
                    final_draft=None,
                    assignee_name=self.default_name,
                    assignee_email=self.default_email,
                    execution_logs=full_log_text
                )
                return "Fallback"
            except:
                return "Error"

    def _cleanup_logger(self):
        logging.getLogger().removeHandler(self.log_handler)
        logging.getLogger("crewai").removeHandler(self.log_handler)