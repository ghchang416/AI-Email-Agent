import requests
import logging
from typing import Tuple, Optional
from crewai.flow.flow import Flow, start, listen, router
from crews.filtering.crew import FilteringCrew
from crews.drafting.crew import DraftingCrew
from crews.routing.crew import RoutingCrew
from schemas.request_io import EmailInput, EmailFlowState
from schemas.task_output import DraftValidation, EmailAnalysis, FinalAssigneeResult
from tools import send_task_to_kanban_tool
from utils import config

logger = logging.getLogger(__name__)

class EmailProcessingFlow(Flow[EmailFlowState]):
    """ @router를 사용하여 카테고리별 로직을 명확히 분리한 이메일 플로우 """
    MAX_RETRIES = 1
    MAX_ROUTING_ATTEMPTS = 3
    spam_webhook_url = config.N8N_SPAM_PROCESS_WEBHOOK_URL
    reply_webhook_url = config.N8N_SEND_REPLY_WEBHOOK_URL
    default_name = config.DEFAULT_MANAGER_NAME
    default_email = config.DEFAULT_MANAGER_EMAIL
    
    @start()
    def start_flow(self):
        email = getattr(self, "_email_input", None)
        self.state.email_data = email
        return email

    @listen(start_flow)
    def run_filtering(self, email_data: EmailInput) -> EmailAnalysis:
        logger.info("Running filtering crew...")
        inputs = {
            "sender": email_data.sender,
            "subject": email_data.subject,
            "body": email_data.body
        }
        result: EmailAnalysis = FilteringCrew().crew().kickoff(inputs=inputs).pydantic
        self.state.analysis_result = result
        logger.info(f"Filtering complete. Category: {result.category}")
        return result
    
    @router(run_filtering) 
    def route_email(self, analysis: EmailAnalysis) -> str:
        logger.info(f"Routing based on category: {analysis.category}")
        return analysis.category

    @listen("OTHER")
    def handle_other(self):
        try:
            payload = {"message_id": self.state.email_data.message_id}
            requests.post(self.spam_webhook_url, json=payload)
        except Exception as e:
            logger.error(f"Failed to call n8n send webhook: {e}")
        return "Flow finished for OTHER."

    @listen("TASK")
    def handle_task(self) -> Tuple[str, Optional[str]]:
        logger.info(f"Action: Running Routing and Scheduling...")
        email_summary = self.state.analysis_result.summary
        email_data = self.state.email_data

        excluded_assignees_list = [] 
        self.state.final_assignee_result: FinalAssigneeResult = None # type: ignore
        
        routing_succeeded = False

        for attempt in range(self.MAX_ROUTING_ATTEMPTS):
            logger.info(f"Routing attempt {attempt + 1}/{self.MAX_ROUTING_ATTEMPTS}...")

            routing_inputs = {
                "sender": email_data.sender,
                "subject": email_data.subject,
                "body": email_data.body,
                "email_summary": email_summary,
                "excluded_assignees_list": excluded_assignees_list
            }

            try:
                final_result: FinalAssigneeResult = RoutingCrew().crew().kickoff(inputs=routing_inputs).pydantic

                if not final_result:
                     logger.warning("Routing crew returned an empty result. Retrying...")
                     continue 
                
                if final_result.status == 'Success':
                    logger.info(f"Routing complete. Final Assignee: {final_result.final_assignee_name} ({final_result.final_assignee_email})")
                    self.state.final_assignee_result = final_result
                    routing_succeeded = True
                    break
                
                else:
                    logger.warning(f"Routing attempt failed. Reason: {final_result.reasoning}")
                    excluded_assignees_list.append(final_result.final_assignee_email)
                    logger.info(f"Adding to exclusion list: {final_result.final_assignee_email}")
            
            except Exception as e:
                logger.error(f"[ERROR] RoutingCrew kickoff failed (Attempt {attempt + 1}): {e}", exc_info=True)
        
        if not routing_succeeded:
            logger.error(f"All {self.MAX_ROUTING_ATTEMPTS} routing attempts failed. Assigning to default manager.")
            self.state.final_assignee_result = FinalAssigneeResult(
                final_assignee_name=self.default_name,
                final_assignee_email=self.default_email,
                status="Success",
                reasoning="All routing attempts failed. Default assignment."
            )

        assigned_to_email = self.state.final_assignee_result.final_assignee_email
        logger.info(f"Final assigned email for drafting: {assigned_to_email}")
               
        final_draft = self._run_drafting_crew()
        return final_draft
    
    @listen("Simple_Inquiry")
    def handle_inquiry(self) -> Optional[str]:
        final_draft = self._run_drafting_crew()
        return final_draft

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
            logger.info(f"Drafting attempt {attempts}...")
            
            crew_result = DraftingCrew().crew().kickoff(inputs=inputs_for_crew)
            validation: DraftValidation = crew_result.pydantic
            
            if validation and validation.passed:
                validation_passed = True
                final_draft = crew_result.tasks_output[0].raw
                logger.info("Validation PASSED.")
            else:
                critique = validation.critique if validation else "Pydantic parsing failed."
                logger.info(f"Validation FAILED. Critique: {critique}")
                inputs_for_crew['last_critique'] = critique
        
        return final_draft

    @listen(handle_task)
    def handle_task_post_action(self, final_draft: Optional[str]):
        
        if not final_draft:
            return logger.error("handle_task_post_action: Draft is None, running failure handler.")
        
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
                assignee_email=assignee_data.final_assignee_email
            )
            
            if success:
                return "Task_Created_In_Kanban"
            else:
                return "Task_Webhook_Failed"
                
        except Exception as e:
            return logger.error(f"Failed to process handle_task_post_action: {e}", exc_info=True)
        
    @listen(handle_inquiry)
    def handle_inquiry_post_action(self, final_draft: Optional[str]):
        """Directory_Inquiry 초안 생성 후속 조치 (웹훅 전송)"""

        if not final_draft:
            return logger.error(f"Failed to generate valid draft after {self.MAX_RETRIES} attempts.")
        
        email_data = self.state.email_data
        logger.info("Action: Calling n8n webhook to send reply...")
        try:
            payload = {
                "message_id": email_data.message_id,
                "content": final_draft
            }
            requests.post(self.reply_webhook_url, json=payload)
        except Exception as e:
            logger.error(f"Failed to call n8n send webhook: {e}")
        return "Inquiry_Answered"