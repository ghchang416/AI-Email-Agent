from typing import List, Any, Optional, Callable
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai.agents.agent_builder.base_agent import BaseAgent
from tools import adaptive_rag_search_tool

@CrewBase
class SoftwareCollegeCrew:
    """
    소프트웨어융합대학 정보 검색 크루
    Agent가 직접 도구를 선택하여 정보를 가져옵니다.
    """
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def info_retrieval_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['info_retrieval_agent'],
            tools=[adaptive_rag_search_tool], 
            verbose=True
        )

    @task
    def retrieve_info_task(self) -> Task:
        return Task(config=self.tasks_config['retrieve_info_task'])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )

    def get_information(self, query: str, step_callback: Optional[Callable] = None, task_callback: Optional[Callable] = None) -> str:
        # Crew 인스턴스 생성
        crew_instance = self.crew()
        
        # 로그 콜백 연결
        if step_callback:
            crew_instance.step_callback = step_callback
        if task_callback:
            crew_instance.task_callback = task_callback
            
        result = crew_instance.kickoff(inputs={'query': query})
        return str(result.raw)