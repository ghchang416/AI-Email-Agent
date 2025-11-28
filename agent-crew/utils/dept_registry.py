from typing import Dict, Any

# 각 부서의 Crew 클래스
from crews.departments.software_college.crew import SoftwareCollegeCrew
# from crews.departments.scholarship.crew import ScholarshipCrew

class DepartmentRegistry:
    """
    대학 내 모든 부서(Crew)를 등록하는 레지스트리
    """
    
    # 1. 부서 ID와 Crew Class 매핑
    _CREW_MAP = {
        "SOFTWARE_COLLEGE": SoftwareCollegeCrew,
        # "SCHOLARSHIP_TEAM": ScholarshipCrew,
    }

    # 2. 부서별 역할 설명 (Manager 라우팅용)
    _DEPT_DESCRIPTION = {
        "SOFTWARE_COLLEGE": "소프트웨어융합대학 소속 학과(SW, 보안 등)의 학사, 졸업, 수강신청, 휴학 승인.",
        # "SCHOLARSHIP_TEAM": "국가/교내 장학금, 학자금 대출 등 재정 지원 관련 문의.",
    }

    # 3. 부서별 페르소나 (Common Drafter 주입용)
    _DEPT_PERSONA = {
        "SOFTWARE_COLLEGE": "당신은 '소프트웨어융합대학 교학팀'입니다. 학생의 학업 성공을 지원하며, 규정에 근거하여 명확하고 친절하게 안내합니다.",
        # "SCHOLARSHIP_TEAM": "당신은 '장학복지팀'입니다. 금전적 문제이므로 매우 정확하고 보수적으로 규정을 안내하되, 학생의 어려움에 공감하는 태도를 가집니다.",
    }

    @classmethod
    def get_crew(cls, dept_id: str):
        return cls._CREW_MAP.get(dept_id)

    @classmethod
    def get_all_descriptions(cls) -> str:
        return "\n".join([f"- {k}: {v}" for k, v in cls._DEPT_DESCRIPTION.items()])

    @classmethod
    def get_persona(cls, dept_id: str) -> str:
        return cls._DEPT_PERSONA.get(dept_id, "당신은 대학 행정 담당자입니다.")