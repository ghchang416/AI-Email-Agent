from typing import List
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai.agents.agent_builder.base_agent import BaseAgent
from schemas.task_output import RoutingResult, FinalAssigneeResult, DutyValidationResult
from tools import search_org_chart_tool, get_kanban_user_status_tool

@CrewBase
class RoutingCrew:
    
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def email_routing_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['email_routing_agent'],
            tools=[search_org_chart_tool],
            verbose=True,
        )

    @agent
    def assignee_validation_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['assignee_validation_agent'],
            tools=[
                search_org_chart_tool,      # 업무 검증용
                get_kanban_user_status_tool # 스케줄 검증용
            ],
            verbose=True,
        )

    @task
    def routing_task(self) -> Task:
        return Task(
            config=self.tasks_config['routing_task'],
            output_pydantic=RoutingResult
        )

    @task
    def validate_duty_task(self) -> Task:
        """[STEP 1] 업무 적절성 검증 태스크"""
        return Task(
            config=self.tasks_config['validate_duty_task'],
            context=[self.routing_task()],
            output_pydantic=DutyValidationResult 
        )

    @task
    def validate_schedule_task(self) -> Task:
        """[STEP 2] 스케줄 가용성 검증 태스크"""
        return Task(
            config=self.tasks_config['validate_schedule_task'],
            context=[self.routing_task(), self.validate_duty_task()],
            output_pydantic=FinalAssigneeResult 
        )
        
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
    