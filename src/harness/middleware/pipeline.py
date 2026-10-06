from abc import ABC, abstractmethod

from harness.core.types import HarnessState


class BaseInterceptor(ABC):
    @abstractmethod
    async def pre_node(self, state: HarnessState, node_name: str) -> HarnessState:
        return state

    @abstractmethod
    async def post_node(self, state: HarnessState, node_name: str) -> HarnessState:
        return state


class MiddlewarePipeline:
    def __init__(self, interceptors: list[BaseInterceptor]) -> None:
        self.interceptors = interceptors

    async def run_pre(self, state: HarnessState, node_name: str) -> HarnessState:
        for interceptor in self.interceptors:
            state = await interceptor.pre_node(state, node_name)
        return state

    async def run_post(self, state: HarnessState, node_name: str) -> HarnessState:
        for interceptor in reversed(self.interceptors):
            state = await interceptor.post_node(state, node_name)
        return state
