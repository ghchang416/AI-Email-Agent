from typing import List
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai.agents.agent_builder.base_agent import BaseAgent
from schemas.task_output import RoutingResult, FinalAssigneeResult
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
    def validate_assignee_task(self) -> Task:
        return Task(
            config=self.tasks_config['validate_assignee_task'],
            context_tasks=[self.find_primary_assignee_task()],
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
    