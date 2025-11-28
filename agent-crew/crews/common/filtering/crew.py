from typing import List
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
from crewai.agents.agent_builder.base_agent import BaseAgent
from schemas.task_output import EmailAnalysis

@CrewBase
class FilteringCrew():
    
    agents: List[BaseAgent]
    tasks: List[Task]
    
    @agent
    def email_filter_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['email_filter_agent'],
            verbose=True
        )
        
    @task
    def triage_email_task(self) -> Task:
        return Task(
            config=self.tasks_config['triage_email_task'],
            output_pydantic=EmailAnalysis
        )
        
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )