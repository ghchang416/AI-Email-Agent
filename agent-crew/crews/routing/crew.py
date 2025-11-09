from typing import List
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai.agents.agent_builder.base_agent import BaseAgent
from schemas.schemas import RoutingResult
from tools.tools import search_org_chart_tool

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

    @task
    def routing_task(self) -> Task:
        return Task(
            config=self.tasks_config['routing_task'],
            output_pydantic=RoutingResult
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
    