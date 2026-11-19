"""Request-scoped LangGraph orchestration over the internal FastMCP client."""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any, TypedDict

from fastapi import HTTPException
from fastmcp import Client
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langsmith import tracing_context

from ..config import Settings
from ..schemas import ChatQuestion
from .presentation import tool_trace
from .server import CATALOG

MAX_DECISIONS = 3
ToolOutput = tuple[str, dict[str, Any], dict[str, Any]]


@dataclass(frozen=True)
class AgentContext:
    settings: Settings
    payload: ChatQuestion
    session: Client
    system_prompt: str
    decide: Callable[..., Awaitable[dict]]
    authorize: Callable[..., bool]
    invoke: Callable[..., Awaitable[dict]]
    finish: Callable[..., dict]
    summarize: Callable[..., Awaitable[dict]] | None = None
    direct: tuple[str, dict] | None = None


class AgentState(TypedDict, total=False):
    messages: list[dict]
    tools: list[dict]
    decisions: int
    decision: dict
    name: str
    arguments: dict
    writing: bool
    results: list[ToolOutput]
    traces: list[dict]
    usage: dict[str, int] | None
    route: str
    answer: dict


async def prepare_tools(state: AgentState, runtime: Runtime[AgentContext]):
    context = runtime.context
    initial = {'results': [], 'traces': [], 'usage': None, 'decisions': 0, 'messages': [], 'tools': []}
    if context.direct is not None:
        name, arguments = context.direct
        return {**initial, 'name': name, 'arguments': arguments, 'route': 'authorize_tool'}
    listing = await context.session.list_tools()
    return {**initial, 'route': 'select_tool',
        'tools': [{'type': 'function', 'function': {'name': t.name, 'description': t.description,
                  'parameters': t.input_schema}} for t in listing],
        'messages': [{'role': 'system', 'content': context.system_prompt}, {'role': 'user', 'content': json.dumps({
            'current_question': context.payload.question,
            'history_for_context_only': [t.model_dump(exclude={'answer'}) for t in context.payload.history]}, ensure_ascii=False)}]}


async def select_tool(state: AgentState, runtime: Runtime[AgentContext]):
    message = await runtime.context.decide(runtime.context.settings, state['messages'], state['tools'])
    usage = state['usage']
    if reported := message.get('_usage'):
        usage = {key: (usage or {}).get(key, 0) + reported[key] for key in ('inputTokens', 'outputTokens')}
    calls = message.get('tool_calls') or []
    if not calls:
        route = 'format_answer' if state['results'] else 'clarify'
    elif len(calls) != 1:
        raise HTTPException(502, 'Agent 每步只能选择一个工具，本次未执行该步骤。')
    else:
        route = 'authorize_tool'
    return {'decision': message, 'decisions': state['decisions'] + 1, 'usage': usage, 'route': route}


def authorize_tool(state: AgentState, runtime: Runtime[AgentContext]):
    context = runtime.context
    if context.direct is not None:
        name, args = state['name'], state['arguments']
    else:
        call = state['decision']['tool_calls'][0]
        try:
            name = call['function']['name']
            args = json.loads(call['function']['arguments'])
            if name not in CATALOG or not isinstance(args, dict) or not isinstance(call['id'], str):
                raise ValueError('Invalid tool')
        except (KeyError, TypeError, ValueError):
            raise HTTPException(502, 'Agent 工具参数无效，本次未执行该步骤。') from None
    # The model may choose a tool, but it cannot rewrite the original question/history.
    if name == 'herbal_reference' and args.get('action') == 'ask':
        args = {**args, 'query': context.payload.question,
                'history': [t.model_dump() for t in context.payload.history]}
    if name == 'data_center' and args.get('action') == 'question':
        args = {**args, 'question': context.payload.question,
                'history': [t.model_dump() for t in context.payload.history]}
    writing = context.authorize(context.payload.question, name, args, state['results'])
    if writing:
        args = {**args, 'confirmed': True}
    try:
        CATALOG[name][0].model_validate(args)
    except ValueError:
        raise HTTPException(502, 'Agent 工具参数无效，本次未执行该步骤。') from None
    duplicate = any(n == name and a == args for n, a, _ in state['results'])
    return {'name': name, 'arguments': args, 'writing': writing,
            'route': 'format_answer' if duplicate else 'execute_tool'}


async def execute_tool(state: AgentState, runtime: Runtime[AgentContext]):
    context = runtime.context
    name, args = state['name'], state['arguments']
    started = perf_counter()
    data = await context.invoke(context.session, name, args)
    results = [*state['results'], (name, args, data)]
    traces = [*state['traces'], tool_trace(name, args, data, (perf_counter() - started) * 1000)]
    stop = (context.direct is not None or state['writing'] or name == 'herbal_reference'
            or name == 'test_execution' and args.get('action') == 'progress'
            or data.get('stale') or data.get('error') or state['decisions'] >= MAX_DECISIONS)
    update = {'results': results, 'traces': traces, 'route': 'format_answer' if stop else 'select_tool'}
    if not stop:
        message = state['decision']
        update['messages'] = [*state['messages'],
            {'role': 'assistant', 'content': message.get('content'), 'tool_calls': message['tool_calls']},
            {'role': 'tool', 'tool_call_id': message['tool_calls'][0]['id'],
             'content': json.dumps(data, ensure_ascii=False)[:50000]}]
    return update


async def format_answer(state: AgentState, runtime: Runtime[AgentContext]):
    context = runtime.context
    answer = context.finish(state['results'], context.payload.question, state['traces'], state['usage'])
    if context.summarize is not None:
        answer = await context.summarize(context.settings, context.payload.question, state['results'], answer)
    return {'answer': answer}


def clarify(state: AgentState):
    return {'answer': {'mode': 'clarification', 'title': '请明确要查询或执行的内容',
        'introduction': '本次尚未调用工具，也未修改数据。', 'sources': [], 'sections': [{
            'title': '可调用模块', 'content': '可查询中药基础资料、数据中心、运行总览、批次记录与测试方案；生成批次请写明数量，修改默认用时请写明设备和分钟数。'}]}}


def next_node(state: AgentState):
    return state['route']


def build_graph():
    graph = StateGraph(AgentState, context_schema=AgentContext)
    for node in (prepare_tools, select_tool, authorize_tool, execute_tool, format_answer, clarify):
        # No retry policy: a failed write must never be resubmitted by the graph.
        graph.add_node(node.__name__, node)
    graph.add_edge(START, 'prepare_tools')
    graph.add_conditional_edges('prepare_tools', next_node, ['select_tool', 'authorize_tool'])
    graph.add_conditional_edges('select_tool', next_node, ['authorize_tool', 'format_answer', 'clarify'])
    graph.add_conditional_edges('authorize_tool', next_node, ['execute_tool', 'format_answer'])
    graph.add_conditional_edges('execute_tool', next_node, ['select_tool', 'format_answer'])
    graph.add_edge('format_answer', END)
    graph.add_edge('clarify', END)
    return graph.compile()


CHAT_GRAPH = build_graph()


async def run_workflow(context: AgentContext):
    # The graph has no checkpointer/store; credentials and live clients stay in runtime context.
    # Match the prescription graph's policy: no remote traces containing business data.
    with tracing_context(enabled=False):
        result = await CHAT_GRAPH.ainvoke({}, context=context, config={'recursion_limit': 4 * MAX_DECISIONS + 4})
    return result['answer']
