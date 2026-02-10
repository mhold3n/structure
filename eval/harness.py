import os
import json
import asyncio
from typing import List, Dict, Any, Callable
from pydantic import BaseModel

from eval.metrics import Metric, MetricResult


class TestExample(BaseModel):
    id: str
    input: str
    expected_output: Any
    context: Dict[str, Any] = {}


class EvaluationResult(BaseModel):
    example_id: str
    metrics: Dict[str, MetricResult]
    output: Any


class TestHarness:
    """
    Manages the test dataset (from Test partition) and evaluation execution.
    """

    def __init__(self, test_partition_path: str = "indexes/test/documents"):
        self.test_partition_path = test_partition_path
        self.examples = self._load_examples()

    def _load_examples(self) -> List[TestExample]:
        examples = []
        if os.path.exists(self.test_partition_path):
            for root, _, files in os.walk(self.test_partition_path):
                for file in files:
                    if file.endswith(".json"):
                        with open(os.path.join(root, file), "r") as f:
                            doc = json.load(f)
                            # Mapping Document to TestExample (simplified for now)
                            # In reality, TestExample needs more structure than raw Document
                            # For this prototype, we treat content as input
                            examples.append(
                                TestExample(
                                    id=doc.get("id"),
                                    input=doc.get("content"),
                                    expected_output=None,  # Or derive from metadata
                                )
                            )
        return examples

    async def evaluate(
        self, workflow_runner: Callable[[str], Any], metrics: List[Metric]
    ) -> List[EvaluationResult]:
        """
        Run the workflow against all examples and compute metrics.
        """
        results = []
        for example in self.examples:
            # Run System
            try:
                output = await workflow_runner(example.input)
            except Exception as e:
                output = str(e)  # Capture error as output

            # Compute Metrics
            metric_results = {}
            for metric in metrics:
                res = metric.compute(example.input, output, example.expected_output)
                metric_results[metric.name] = res

            results.append(
                EvaluationResult(example_id=example.id, metrics=metric_results, output=str(output))
            )

        return results
