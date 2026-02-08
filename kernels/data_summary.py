from typing import List, Dict, Any
import re
from collections import Counter
from kernels.base import KernelInterface, register_kernel
from models.kernel_io import KernelInput, KernelOutput


@register_kernel
class DataSummaryKernel(KernelInterface):
    """
    Deterministic kernel for text and data summarization.
    """

    kernel_id = "data_summary_v1"
    version = "1.0.0"
    determinism_level = "D1"
    description = "Extractive summarization and data aggregation."

    def validate_args(self, args: dict) -> tuple[bool, list[str]]:
        errors = []
        if "method" not in args:
            errors.append("Missing 'method' argument")

        if args.get("method") in ["extractive", "frequency"] and "text" not in args:
            errors.append("Missing 'text' argument")
        return len(errors) == 0, errors

    def execute(self, input: KernelInput) -> KernelOutput:
        args = input.args
        valid, errors = self.validate_args(args)
        if not valid:
            return self._make_output(
                input.request_id, success=False, error="Invalid arguments: " + "; ".join(errors)
            )

        method = args.get("method")
        text = args.get("text")

        if method == "extractive":
            output = self._extractive_summary(text, count=args.get("count", 3))
            return self._make_output(
                input.request_id, success=output.success, result=output.result, error=output.error
            )
        elif method == "frequency":
            output = self._frequency_dist(text)
            return self._make_output(
                input.request_id, success=output.success, result=output.result, error=output.error
            )
        else:
            return self._make_output(
                input.request_id, success=False, error=f"Unknown method '{method}'"
            )

    def _extractive_summary(self, text: str, count: int) -> KernelOutput:
        # 1. Split sentences
        sentences = re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s", text)

        # 2. Score sentences (simple word freq)
        words = re.findall(r"\w+", text.lower())
        word_freq = Counter(words)

        scores = []
        for i, sent in enumerate(sentences):
            sent_words = re.findall(r"\w+", sent.lower())
            if not sent_words:
                scores.append((i, 0))
                continue
            score = sum(word_freq[w] for w in sent_words) / len(sent_words)
            scores.append((i, score))

        # 3. Pick top N
        top_indices = sorted(scores, key=lambda x: x[1], reverse=True)[:count]
        top_indices = sorted([x[0] for x in top_indices])  # Reorder by original position

        summary = [sentences[i] for i in top_indices]

        return KernelOutput(success=True, result={"summary": " ".join(summary)})

    def _frequency_dist(self, text: str) -> KernelOutput:
        words = re.findall(r"\w+", text.lower())
        return KernelOutput(success=True, result=dict(Counter(words).most_common(20)))
