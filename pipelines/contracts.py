from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Any
from pydantic import BaseModel

T_Input = TypeVar("T_Input")
T_Output = TypeVar("T_Output")


class PipelineContext(BaseModel):
    """
    Shared context passed through the pipeline stages.
    """

    run_id: str
    config: dict = {}
    dry_run: bool = False


class PipelineStage(ABC, Generic[T_Input, T_Output]):
    """
    Abstract base class for a single stage in the ingestion pipeline.
    """

    def __init__(self, context: PipelineContext):
        self.context = context

    @abstractmethod
    def run(self, input_data: T_Input) -> T_Output:
        """
        Execute the stage logic.
        """
        pass
