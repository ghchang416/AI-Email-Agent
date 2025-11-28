import os
import logging
from openai import OpenAI
from schemas.task_output import DepartmentRoutingDecision, SupportingDeptDecision
from utils.dept_registry import DepartmentRegistry

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def determine_primary_dept(email_body: str) -> DepartmentRoutingDecision:
    """
    이메일 본문을 분석하여 가장 적합한 주관 부서(Primary Dept)를 선정합니다.
    """
    dept_desc = DepartmentRegistry.get_all_descriptions()
    
    system_prompt = f"""
    You are a router for university administration emails.
    Select ONE Primary Department ID based on the descriptions.
    If irrelevant, mark is_spam as True.

    [Departments]
    {dept_desc}
    """

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": email_body},
            ],
            response_format=DepartmentRoutingDecision,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Primary Dept Selection Failed: {e}")
        return DepartmentRoutingDecision(primary_dept_id="OTHER", is_spam=False)

def find_supporting_dept(query: str, hint: str) -> str | None:
    """
    부족한 정보(Query)와 힌트(Hint)를 바탕으로 이를 해결해 줄 협조 부서를 찾습니다.
    """
    dept_desc = DepartmentRegistry.get_all_descriptions()
    
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Find Dept ID based on capabilities.\nList:\n{dept_desc}"}, 
                {"role": "user", "content": f"Query: {query}\nHint: {hint}"}
            ],
            response_format=SupportingDeptDecision,
        )
        return completion.choices[0].message.parsed.dept_id
    except Exception as e:
        logger.error(f"Supporting Dept Search Failed: {e}")
        return None