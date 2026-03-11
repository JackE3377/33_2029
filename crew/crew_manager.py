# ============================================================
# GEM Protocol — CrewAI Crew Manager (Pipeline Orchestrator)
# ============================================================
"""
Orchestrates the CrewAI agent pipeline.
Composes agents and tasks into executable crews.
Provides both full-pipeline and per-engine execution modes.
"""
from __future__ import annotations

from typing import Any, Optional

from crewai import Crew, Process

from core.logger import get_logger
from crew.agents import (
    create_macro_sentinel,
    create_tether_arbitrageur,
    create_quant_screener,
    create_split_strategist,
    create_portfolio_guardian,
    create_report_synthesiser,
)
from crew.tasks import (
    create_macro_analysis_task,
    create_tether_analysis_task,
    create_stock_screening_task,
    create_split_strategy_task,
    create_rebalance_task,
    create_daily_report_task,
)

logger = get_logger("crew_manager")


class GEMCrewManager:
    """
    Manages CrewAI agent crews for the GEM Protocol.
    
    Supports two execution modes:
      1. Full pipeline — all agents run sequentially
      2. Targeted — run specific agent(s) for a single engine
    """

    def __init__(self):
        # Lazily create agents
        self._agents: dict[str, Any] = {}

    def _get_agent(self, name: str):
        """Lazily initialise agents to avoid unnecessary API calls."""
        if name not in self._agents:
            factories = {
                "macro": create_macro_sentinel,
                "tether": create_tether_arbitrageur,
                "screener": create_quant_screener,
                "strategist": create_split_strategist,
                "guardian": create_portfolio_guardian,
                "synthesiser": create_report_synthesiser,
            }
            self._agents[name] = factories[name]()
        return self._agents[name]

    def run_macro_analysis(self, macro_data: dict) -> str:
        """Run macro sentinel analysis only."""
        agent = self._get_agent("macro")
        task = create_macro_analysis_task(agent, macro_data)

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        logger.info("Running macro analysis crew...")
        result = crew.kickoff()
        return str(result)

    def run_tether_analysis(self, tether_data: dict) -> str:
        """Run tether arbitrage analysis."""
        agent = self._get_agent("tether")
        task = create_tether_analysis_task(agent, tether_data)

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        logger.info("Running tether analysis crew...")
        result = crew.kickoff()
        return str(result)

    def run_stock_screening(self, candidates: list[dict]) -> str:
        """Run quantitative stock screening."""
        agent = self._get_agent("screener")
        task = create_stock_screening_task(agent, candidates)

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        logger.info("Running stock screening crew...")
        result = crew.kickoff()
        return str(result)

    def run_split_strategy(self, positions: list[dict], signals: list[dict]) -> str:
        """Run split buy/sell strategy analysis."""
        agent = self._get_agent("strategist")
        task = create_split_strategy_task(agent, positions, signals)

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        logger.info("Running split strategy crew...")
        result = crew.kickoff()
        return str(result)

    def run_rebalance_analysis(self, portfolio: dict, triggers: list[str]) -> str:
        """Run warehouse rebalancing analysis."""
        agent = self._get_agent("guardian")
        task = create_rebalance_task(agent, portfolio, triggers)

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        logger.info("Running rebalance analysis crew...")
        result = crew.kickoff()
        return str(result)

    def run_full_pipeline(
        self,
        macro_data: dict,
        tether_data: dict,
        positions: list[dict],
        signals: list[dict],
        portfolio: dict,
        triggers: list[str],
        engine_summaries: dict,
        risk_state: dict,
    ) -> str:
        """
        Run the complete agent pipeline:
        Macro → Tether → Screener → Strategist → Guardian → Synthesiser
        """
        logger.info("Running FULL pipeline crew...")

        # Create all agents
        macro_agent = self._get_agent("macro")
        tether_agent = self._get_agent("tether")
        screener_agent = self._get_agent("screener")
        strategist_agent = self._get_agent("strategist")
        guardian_agent = self._get_agent("guardian")
        synthesiser_agent = self._get_agent("synthesiser")

        # Create all tasks
        tasks = [
            create_macro_analysis_task(macro_agent, macro_data),
            create_tether_analysis_task(tether_agent, tether_data),
            create_stock_screening_task(screener_agent, []),
            create_split_strategy_task(strategist_agent, positions, signals),
            create_rebalance_task(guardian_agent, portfolio, triggers),
            create_daily_report_task(
                synthesiser_agent,
                macro_summary=str(macro_data),
                engine_summaries=engine_summaries,
                risk_state=risk_state,
            ),
        ]

        crew = Crew(
            agents=[
                macro_agent, tether_agent, screener_agent,
                strategist_agent, guardian_agent, synthesiser_agent,
            ],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()
        logger.info("Full pipeline complete")
        return str(result)
