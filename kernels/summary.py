from typing import List, Dict, Any
import re
from collections import Counter
from kernels.base import KernelInterface
from models.kernel_io import KernelInput, KernelOutput


class SummaryKernel(KernelInterface):
    """
    Deterministic kernel for text and data summarization.
    """

    kernel_id = "summary_v1"
    description = "Extractive summarization and data aggregation."

    def execute(self, input: KernelInput) -> KernelOutput:
        method = input.args.get("method")
        text = input.args.get("text")

        if method == "extractive":
            if not text:
                return KernelOutput(success=False, error="Method 'extractive' requires 'text' arg")
            return self._extractive_summary(text, count=input.args.get("count", 3))
        elif method == "frequency":
            if not text:
                return KernelOutput(success=False, error="Method 'frequency' requires 'text' arg")
            return self._frequency_dist(text)
        else:
            return KernelOutput(success=False, error=f"Unknown method '{method}'")

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
