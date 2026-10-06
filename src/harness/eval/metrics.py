import re
from typing import Any

STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "when",
    "at",
    "by",
    "for",
    "with",
    "about",
    "against",
    "between",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "to",
    "from",
    "up",
    "down",
    "in",
    "out",
    "on",
    "off",
    "over",
    "under",
    "again",
    "further",
    "once",
    "here",
    "there",
    "all",
    "any",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "s",
    "t",
    "can",
    "will",
    "just",
    "don",
    "should",
    "now",
    "is",
    "was",
    "are",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "having",
    "do",
    "does",
    "did",
    "doing",
    "reached",
    "lasted",
}


def _tokenize_content(text: str) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    content_words = {w for w in words if w not in STOP_WORDS}
    return content_words if content_words else set(words)


class ToolCallFidelityScorer:
    """Scores accuracy of tool selection and argument correctness."""

    def score(
        self,
        selected_tool: str,
        expected_tool: str,
        actual_arguments: dict[str, Any],
        expected_arguments: dict[str, Any],
    ) -> float:
        if selected_tool != expected_tool:
            return 0.0

        if not expected_arguments:
            return 1.0

        correct_args = 0
        for key, val in expected_arguments.items():
            if key in actual_arguments and actual_arguments[key] == val:
                correct_args += 1

        return correct_args / len(expected_arguments)


class GroundednessScorer:
    """Measures faithfulness/groundedness of answer against provided context."""

    def score(self, context: str, answer: str) -> float:
        ctx_tokens = _tokenize_content(context)
        ans_tokens = _tokenize_content(answer)

        if not ans_tokens:
            return 0.0

        overlap = ans_tokens.intersection(ctx_tokens)
        return len(overlap) / len(ans_tokens)


class AnswerRelevancyScorer:
    """Measures relevancy of generated answer to original user prompt."""

    def score(self, question: str, answer: str) -> float:
        q_tokens = _tokenize_content(question)
        a_tokens = _tokenize_content(answer)

        if not q_tokens or not a_tokens:
            return 0.0

        overlap = q_tokens.intersection(a_tokens)
        return len(overlap) / len(q_tokens)
