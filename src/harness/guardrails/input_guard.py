import re

from harness.core.exceptions import PromptInjectionDetected
from harness.core.types import AgentMessage, HarnessState, Role
from harness.middleware.pipeline import BaseInterceptor

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+|previous\s+)?instructions", re.IGNORECASE),
    re.compile(r"ignore\s+all\s+previous\s+rules", re.IGNORECASE),
    re.compile(r"dump\s+secrets", re.IGNORECASE),
    re.compile(r"reveal\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"print\s+api\s+keys?", re.IGNORECASE),
]

SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


class InputGuardInterceptor(BaseInterceptor):
    def __init__(self, redact_pii: bool = True) -> None:
        self.redact_pii = redact_pii

    def _detect_prompt_injection(self, text: str) -> None:
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                raise PromptInjectionDetected(
                    f"Prompt injection detected matching pattern: '{pattern.pattern}'"
                )

    def _redact_pii_content(self, text: str) -> str:
        text = SSN_REGEX.sub("[REDACTED_SSN]", text)
        text = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
        return text

    async def pre_node(self, state: HarnessState, node_name: str) -> HarnessState:
        if not state.messages:
            return state

        updated_messages: list[AgentMessage] = []
        for msg in state.messages:
            if msg.role == Role.USER and msg.content:
                # 1. Prompt Injection Filter
                self._detect_prompt_injection(msg.content)

                # 2. PII / PHI Redaction
                if self.redact_pii:
                    sanitized_content = self._redact_pii_content(msg.content)
                    if sanitized_content != msg.content:
                        msg = AgentMessage(
                            role=msg.role,
                            content=sanitized_content,
                            tool_calls=msg.tool_calls,
                            tool_call_id=msg.tool_call_id,
                            name=msg.name,
                        )
            updated_messages.append(msg)

        state.messages = updated_messages
        return state

    async def post_node(self, state: HarnessState, node_name: str) -> HarnessState:
        return state
