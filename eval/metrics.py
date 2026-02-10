from abc import ABC, abstractmethod
from typing import Any, Union
from pydantic import BaseModel
import time

class MetricResult(BaseModel):
    score: float
    details: dict = {}


class Metric(ABC):
    """
    Abstract base class for an evaluation metric.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def compute(self, input_data: Any, output_data: Any, expected: Any) -> MetricResult:
        pass


class LatencyMetric(Metric):
    """
    Measures execution time (mocked for now as we don't have start/end times here).
    """
    @property
    def name(self) -> str:
        return "latency"

    def compute(self, input_data: Any, output_data: Any, expected: Any) -> MetricResult:
        # Placeholder
        return MetricResult(score=0.0)


class CostMetric(Metric):
    """
    Measures token cost (mocked).
    """
    @property
    def name(self) -> str:
        return "cost"

    def compute(self, input_data: Any, output_data: Any, expected: Any) -> MetricResult:
        # Placeholder
        return MetricResult(score=0.0)
        

class ExactMatchMetric(Metric):
    """
    Checks if output strictly matches expected.
    """
    @property
    def name(self) -> str:
        return "exact_match"

    def compute(self, input_data: Any, output_data: Any, expected: Any) -> MetricResult:
        if expected is None:
             return MetricResult(score=0.0, details={"error": "No expected value"})
             
        score = 1.0 if str(output_data).strip() == str(expected).strip() else 0.0
        return MetricResult(score=score)
