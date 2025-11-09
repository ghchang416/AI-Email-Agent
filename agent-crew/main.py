from fastapi import FastAPI, BackgroundTasks
from flow import EmailProcessingFlow
from schemas.request_io import EmailInput

app = FastAPI()

@app.post("/run")
async def start_email_flow(email_input: EmailInput, background_tasks: BackgroundTasks):
    """
    n8n이 이메일 처리를 요청하는 엔드포인트.
    Flow는 완료까지 시간이 걸리므로 백그라운드에서 실행합니다.
    """
    
    def run_flow_in_background(email_input: EmailInput):
        try:
            flow = EmailProcessingFlow()
            flow._email_input = email_input
            flow.kickoff()
            print("Background flow finished successfully.")
        except Exception as e:
            print(f"Error during background flow execution: {e}")

    background_tasks.add_task(run_flow_in_background, email_input)
    return {"message": "Email processing flow started in background."}