from typing import List
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai.agents.agent_builder.base_agent import BaseAgent
from schemas.task_output import DraftValidation, DraftOutput

@CrewBase
class DraftingCrew:
    """ 공통 작문 크루"""
    
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def response_generation_agent(self) -> Agent:
        return Agent(config=self.agents_config['response_generation_agent'], verbose=True)

    @agent
    def draft_validation_agent(self) -> Agent:
        return Agent(config=self.agents_config['draft_validation_agent'], verbose=True)

    @task
    def draft_response_task(self) -> Task:
        return Task(config=self.tasks_config['draft_response_task'], output_pydantic=DraftOutput)

    @task
    def validate_draft_task(self) -> Task:
        return Task(config=self.tasks_config['validate_draft_task'], output_pydantic=DraftValidation)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )