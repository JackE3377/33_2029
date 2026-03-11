# ============================================================
# GEM Protocol — Multi-LLM Router with Caching & Budget Control
# ============================================================
"""
Routes tasks to the optimal LLM based on complexity:
  - Simple parsing/classification → Gemini Flash Lite (cheapest)
  - Deep quant analysis           → Gemini Flash / GPT-5
  - Fallback chain                → Gemini → GPT → Rule-based

Includes:
  - Response caching (TTL-based)
  - Monthly budget tracking
  - Token usage logging
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from core.config import get_settings
from core.logger import get_logger
from core.models import LLMUsageLog, get_session

logger = get_logger("llm_router")


# ---------- Task Complexity ----------

class TaskComplexity(str, Enum):
    LIGHT = "light"      # Parsing, classification, simple Q&A
    MEDIUM = "medium"    # Summarisation, data extraction
    HEAVY = "heavy"      # Deep quant analysis, multi-step reasoning


# ---------- Model Catalog ----------

@dataclass
class ModelSpec:
    name: str
    provider: str  # "gemini" or "openai"
    cost_per_1k_input: float   # USD
    cost_per_1k_output: float  # USD
    max_tokens: int


MODEL_CATALOG: dict[str, ModelSpec] = {
    "gemini-flash-lite": ModelSpec(
        name="gemini-2.0-flash-lite",
        provider="gemini",
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        max_tokens=8192,
    ),
    "gemini-flash": ModelSpec(
        name="gemini-2.0-flash",
        provider="gemini",
        cost_per_1k_input=0.0001,
        cost_per_1k_output=0.0004,
        max_tokens=8192,
    ),
    "gpt-5": ModelSpec(
        name="gpt-4o",
        provider="openai",
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        max_tokens=4096,
    ),
}

# Routing table: complexity → ordered model preference
ROUTING_TABLE: dict[TaskComplexity, list[str]] = {
    TaskComplexity.LIGHT: ["gemini-flash-lite", "gemini-flash"],
    TaskComplexity.MEDIUM: ["gemini-flash", "gpt-5"],
    TaskComplexity.HEAVY: ["gpt-5", "gemini-flash"],
}


# ---------- Cache ----------

class LLMCache:
    """Simple TTL-based in-memory response cache."""

    def __init__(self, default_ttl: int = 300):
        self._store: dict[str, tuple[float, Any]] = {}
        self._default_ttl = default_ttl

    def _key(self, prompt: str, model: str) -> str:
        raw = f"{model}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, model: str) -> Optional[str]:
        key = self._key(prompt, model)
        if key in self._store:
            expiry, value = self._store[key]
            if time.time() < expiry:
                logger.debug(f"Cache hit for model={model}")
                return value
            del self._store[key]
        return None

    def set(self, prompt: str, model: str, response: str, ttl: Optional[int] = None) -> None:
        key = self._key(prompt, model)
        self._store[key] = (time.time() + (ttl or self._default_ttl), response)

    def clear(self) -> None:
        self._store.clear()


# ---------- Budget Tracker ----------

class BudgetTracker:
    """Tracks monthly LLM spend against budget cap."""

    @staticmethod
    def get_monthly_spend() -> float:
        session = get_session()
        try:
            now = datetime.now(timezone.utc)
            first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            logs = (
                session.query(LLMUsageLog)
                .filter(LLMUsageLog.timestamp >= first_of_month)
                .all()
            )
            return sum(log.cost_usd for log in logs)
        finally:
            session.close()

    @staticmethod
    def is_over_budget() -> bool:
        settings = get_settings()
        spent = BudgetTracker.get_monthly_spend()
        return spent >= settings.llm_monthly_budget_usd

    @staticmethod
    def log_usage(model: str, task_type: str, input_tokens: int, output_tokens: int, cost: float):
        session = get_session()
        try:
            session.add(LLMUsageLog(
                model=model,
                task_type=task_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            ))
            session.commit()
        finally:
            session.close()


# ---------- LLM Clients ----------

def _call_gemini(model_name: str, prompt: str, api_key: str) -> tuple[str, int, int]:
    """Call Google Gemini API. Returns (response_text, input_tokens, output_tokens)."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)

    text = response.text or ""
    # Token counts from usage metadata
    usage = getattr(response, "usage_metadata", None)
    input_t = getattr(usage, "prompt_token_count", len(prompt) // 4) if usage else len(prompt) // 4
    output_t = getattr(usage, "candidates_token_count", len(text) // 4) if usage else len(text) // 4

    return text, input_t, output_t


def _call_openai(model_name: str, prompt: str, api_key: str) -> tuple[str, int, int]:
    """Call OpenAI API. Returns (response_text, input_tokens, output_tokens)."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    text = response.choices[0].message.content or ""
    usage = response.usage
    input_t = usage.prompt_tokens if usage else 0
    output_t = usage.completion_tokens if usage else 0

    return text, input_t, output_t


# ---------- Main Router ----------

class LLMRouter:
    """
    Routes prompts to the best-fit LLM with fallback chain.
    
    Usage:
        router = LLMRouter()
        result = router.query("Analyze FCF for AAPL", TaskComplexity.HEAVY)
    """

    def __init__(self):
        self._cache = LLMCache(default_ttl=300)
        self._settings = get_settings()

    def query(
        self,
        prompt: str,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        task_type: str = "general",
        use_cache: bool = True,
        cache_ttl: int = 300,
    ) -> str:
        """
        Send prompt to the best available LLM.
        Falls back through the routing chain on failure.
        Final fallback: returns empty string (let caller use rule-based logic).
        """
        # Budget check
        if BudgetTracker.is_over_budget():
            logger.warning("LLM monthly budget exceeded — falling back to rule-based")
            return ""

        model_chain = ROUTING_TABLE.get(complexity, ROUTING_TABLE[TaskComplexity.MEDIUM])

        for model_key in model_chain:
            spec = MODEL_CATALOG[model_key]

            # Check cache
            if use_cache:
                cached = self._cache.get(prompt, spec.name)
                if cached is not None:
                    return cached

            # Attempt call
            try:
                if spec.provider == "gemini" and self._settings.gemini_api_key:
                    text, in_t, out_t = _call_gemini(
                        spec.name, prompt, self._settings.gemini_api_key
                    )
                elif spec.provider == "openai" and self._settings.openai_api_key:
                    text, in_t, out_t = _call_openai(
                        spec.name, prompt, self._settings.openai_api_key
                    )
                else:
                    logger.debug(f"No API key for {spec.provider}, skipping {model_key}")
                    continue

                # Calculate cost
                cost = (in_t / 1000 * spec.cost_per_1k_input) + (
                    out_t / 1000 * spec.cost_per_1k_output
                )

                # Log usage
                BudgetTracker.log_usage(spec.name, task_type, in_t, out_t, cost)

                # Cache response
                if use_cache:
                    self._cache.set(prompt, spec.name, text, cache_ttl)

                logger.info(
                    f"LLM call: model={spec.name}, in={in_t}, out={out_t}, cost=${cost:.4f}"
                )
                return text

            except Exception as e:
                logger.warning(f"LLM call failed ({model_key}): {e}. Trying next...")
                continue

        logger.error("All LLM models failed — returning empty (use rule-based fallback)")
        return ""

    def clear_cache(self):
        self._cache.clear()
