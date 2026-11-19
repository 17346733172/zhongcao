import asyncio
import json
import secrets
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi.testclient import TestClient
from fastmcp import Client, FastMCP

from app.config import Settings
from app.main import create_app
from app.mcp_tools.agent import authorize_write
from app.mcp_tools.client import BencaoClient, ToolFailure
from app.mcp_tools.commands import requested_creation_count
from app.mcp_tools.server import create_server
from app.security import token_hash
from test_data_center_chat import snapshot


def decision(name, **args):
    return {'role': 'assistant', 'content': None, 'tool_calls': [{
        'id': 'call_1', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}]}


def defaults(revision=2, seconds=60):
    from app.mcp_tools.agent import KINDS
    return {'revision': revision, 'items': [
        {'kind': k, 'name': words[0], 'default_processing_seconds': seconds if k == 'packer' else 60}
        for k, words in KINDS.items()]}


class MCPTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.settings = Settings(rag_enabled=False, database=Path(self.temp.name) / 'test.db',
                                 deepseek_api_key='test-key')
        self.app = create_app(self.settings)
        self.client = TestClient(self.app, headers={'X-CSRF-Protection': '1'})
        self.client.__enter__()
        self.token = secrets.token_urlsafe(24)
        with self.app.state.database.connect() as db:
            cursor = db.execute('INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)',
                                ('mcp_viewer', 'MCP 测试', 'unused', 'viewer', int(time.time())))
            db.execute('INSERT INTO sessions VALUES(?,?,?)', (token_hash(self.token), cursor.lastrowid, time.time() + 600))
        self.client.cookies.set(self.settings.cookie_name, self.token)
        reader = self.app.state.data_center_reader
        reader.data = snapshot()
        reader.fetched_at = datetime.now(timezone.utc)
        reader.start = AsyncMock()
        reader.request_refresh = Mock()
        # Existing routing tests keep their verified text while exercising the new final node.
        synthesis = patch('app.mcp_tools.synthesis.request_json', side_effect=lambda settings, prompt, context, **kwargs:
            json.dumps({'sections': context['verified_answer']['sections'] or [
                {'title': '查询结果', 'content': context['verified_answer']['title']}]}, ensure_ascii=False))
        self.synthesis = synthesis.start()
        self.addCleanup(synthesis.stop)

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def tool(self, name, arguments=None, token=True):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://internal',
                    cookies={self.settings.cookie_name: self.token} if token else {}) as http:
                async with Client(create_server(BencaoClient(http))) as session:
                    return await session.call_tool(name, arguments or {}, raise_on_error=False)
        return asyncio.run(run())

    def ask(self, question):
        return self.client.post('/api/chat', json={'question': question, 'use_knowledge': True})

    def test_initialize_and_list_exactly_five_tools_with_strict_schemas(self):
        async def run():
            async with httpx.AsyncClient() as http:
                server = create_server(BencaoClient(http))
                self.assertIsInstance(server, FastMCP)
                async with Client(server) as session:
                    tools = await session.list_tools()
                    self.assertEqual({t.name for t in tools}, {'herbal_reference', 'data_center', 'operations_overview', 'test_execution', 'test_plans'})
                    for tool in tools:
                        self.assertFalse(tool.input_schema['additionalProperties'])
                    self.assertTrue(next(t for t in tools if t.name == 'data_center').annotations.read_only_hint)
                    self.assertFalse(next(t for t in tools if t.name == 'test_execution').annotations.read_only_hint)
        asyncio.run(run())

    def test_anonymous_and_revoked_sessions_cannot_read_or_write(self):
        self.assertTrue(self.tool('operations_overview', token=False).is_error)
        with self.app.state.database.connect() as db:
            db.execute('DELETE FROM sessions')
        with patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream:
            for name, args in [('operations_overview', {}), ('test_execution', {'action': 'create', 'count': 2, 'confirmed': True})]:
                self.assertTrue(self.tool(name, args).is_error)
            upstream.assert_not_called()

    def test_reference_read_pagination_and_search(self):
        result = self.tool('herbal_reference', {'action': 'read', 'offset': 5, 'limit': 2})
        self.assertFalse(result.is_error)
        self.assertEqual(len(result.structured_content['items']), 2)
        self.assertGreater(result.structured_content['total'], 100)
        found = self.tool('herbal_reference', {'action': 'search', 'query': '陈皮'})
        self.assertIn('陈皮', found.content[0].text)
        missing = self.tool('herbal_reference', {'action': 'search', 'query': '1111111'})
        self.assertEqual(missing.structured_content['items'], [])

    def test_overview_and_running_share_real_time_and_do_not_invent_records(self):
        reader = self.app.state.data_center_reader
        overview = self.tool('operations_overview').structured_content
        self.assertEqual(overview['fetched_at'], reader.fetched_at.isoformat().replace('+00:00', 'Z'))
        self.assertEqual(overview['data']['device_categories']['pot']['total'], 6)
        running = self.tool('test_execution').structured_content
        self.assertEqual(len(running['data']['devices']), 3)
        self.assertEqual(running['data']['batches'], [])
        reader.fetched_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(self.tool('operations_overview').structured_content['stale'])
        reader.data = None
        self.assertIsNone(self.tool('operations_overview').structured_content['data'])

    def test_invalid_or_unconfirmed_writes_never_reach_api(self):
        with patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream:
            cases = [
                ('test_execution', {'action': 'create', 'count': 2}),
                ('test_execution', {'action': 'create', 'count': True, 'confirmed': True}),
                ('test_execution', {'action': 'create', 'count': 51, 'confirmed': True}),
                ('test_execution', {'action': 'start', 'confirmed': True, 'count': 1}),
                ('test_execution', {'action': 'pause', 'confirmed': True, 'url': 'http://evil'}),
                ('test_plans', {'action': 'save', 'kind': 'pot', 'minutes': 2, 'expected_revision': 2, 'confirmed': True}),
                ('test_plans', {'action': 'save', 'kind': 'packer', 'minutes': 121, 'expected_revision': 2, 'confirmed': True}),
                ('data_center', {'action': 'batch', 'batch_id': '../users'}),
            ]
            for name, args in cases:
                with self.subTest(args=args):
                    result = self.tool(name, args)
                    self.assertTrue(result.is_error)
                    self.assertEqual(result.structured_content['status_code'], 422)
                    self.assertNotIn('http://evil', result.content[0].text)
            upstream.assert_not_called()

    def test_command_receipt_and_uncertain_failure_sent_once(self):
        with patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream:
            upstream.return_value = httpx.Response(201, json={'count': 2, 'batch_ids': ['a', 'b']})
            result = self.tool('test_execution', {'action': 'create', 'count': 2, 'confirmed': True})
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content['batch_ids'], ['a', 'b'])
            self.assertEqual(upstream.await_count, 1)
            from fastapi import HTTPException
            upstream.reset_mock()
            upstream.side_effect = HTTPException(502, '未能确认操作结果，系统不会自动重复提交。')
            failed = self.tool('test_execution', {'action': 'start', 'confirmed': True})
            self.assertTrue(failed.is_error)
            self.assertIn('不会自动重复提交', failed.content[0].text)
            self.assertEqual(upstream.await_count, 1)

    def test_plans_minutes_convert_and_revision_conflict_stays_error(self):
        with patch('app.device_defaults.simulation_request', new_callable=AsyncMock) as upstream:
            upstream.return_value = httpx.Response(200, json=defaults(3, 90))
            result = self.tool('test_plans', {'action': 'save', 'kind': 'packer', 'minutes': 1.5, 'expected_revision': 2, 'confirmed': True})
            self.assertFalse(result.is_error)
            self.assertEqual(upstream.call_args.args[-1], {'default_processing_seconds': 90, 'expected_revision': 2})
            upstream.return_value = httpx.Response(409)
            result = self.tool('test_plans', {'action': 'save', 'kind': 'packer', 'minutes': 2, 'expected_revision': 2, 'confirmed': True})
            self.assertTrue(result.is_error)
            self.assertEqual(result.structured_content['status_code'], 409)

    def test_agent_selects_overview_through_mcp_and_formats_actual_data(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            choose.side_effect = [decision('operations_overview'), {'content': '不可信数字999999', 'tool_calls': []}]
            response = self.ask('查看运行总览')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['toolCalls'][0]['name'], 'operations_overview')
        self.assertIn('处方：10', json.dumps(body, ensure_ascii=False))
        self.assertNotIn('999999', json.dumps(body))

    def test_answer_trace_and_chart_come_from_validated_results(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            selected = decision('operations_overview')
            selected['_usage'] = {'inputTokens': 123, 'outputTokens': 45}
            choose.side_effect = [selected, {'content': '已完成', '_usage': {'inputTokens': 20, 'outputTokens': 6}}]
            response = self.ask('查看运行总览')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['usage'], {'inputTokens': 143, 'outputTokens': 51, 'scope': 'tool_selection'})
        trace = body['toolCalls'][0]
        self.assertEqual(trace['status'], 'success')
        self.assertGreaterEqual(trace['durationMs'], 0)
        self.assertIn('fetchedAt', trace)
        self.assertNotIn('arguments', trace)
        chart = body['charts'][0]
        self.assertEqual(chart['title'], '批次状态分布')
        self.assertEqual(chart['series'][0]['values'], [0, 2, 0, 8, 0])
        self.assertEqual(chart['fetchedAt'], trace['fetchedAt'])
        self.assertNotIn('良率', json.dumps(body, ensure_ascii=False))

    def test_final_ai_organizes_tool_results_and_preserves_metadata(self):
        sections = [{'title': '运行情况', 'content': '有 2 个批次正在进行，8 个已完成。'}]
        self.synthesis.side_effect = None
        self.synthesis.return_value = json.dumps({'sections': sections}, ensure_ascii=False)
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            choose.side_effect = [decision('operations_overview'), {'content': '不可信数字999999'}]
            response = self.ask('查看运行总览')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['sections'], sections)
        self.assertEqual(body['mode'], 'data_center')
        self.assertEqual(body['sources'], [])
        self.assertEqual(body['resolvedQuestion'], '查看运行总览')
        self.assertEqual(body['charts'][0]['series'][0]['values'], [0, 2, 0, 8, 0])
        self.assertIn('数据读取时间', body['introduction'])
        self.assertEqual(body['toolCalls'][0]['name'], 'operations_overview')
        self.synthesis.assert_called_once()
        context = self.synthesis.call_args.args[2]
        self.assertEqual(context['current_question'], '查看运行总览')
        self.assertEqual(set(context['verified_answer']), {'title', 'introduction', 'sections'})
        self.assertNotIn(self.token, json.dumps(context))
        self.assertNotIn('999999', json.dumps(context))

    def test_failed_ai_after_successful_write_keeps_receipt_without_resubmitting(self):
        from fastapi import HTTPException
        self.synthesis.side_effect = HTTPException(504, 'upstream-private-detail')
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream:
            choose.return_value = decision('test_execution', action='create', count=2)
            upstream.return_value = httpx.Response(201, json={'count': 2, 'batch_ids': ['a', 'b']})
            response = self.ask('生成2个仿真演示批次')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn('AI 整理暂时未完成', body['introduction'])
        self.assertIn('生成数量：2', body['sections'][0]['content'])
        self.assertIn('a、b', body['sections'][0]['content'])
        self.assertEqual(body['toolCalls'][0]['status'], 'success')
        self.assertNotIn('upstream-private-detail', response.text)
        upstream.assert_awaited_once()
        choose.assert_awaited_once()
        self.synthesis.assert_called_once()

    def test_stale_data_warning_survives_ai_organization(self):
        self.app.state.data_center_reader.fetched_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.synthesis.side_effect = None
        self.synthesis.return_value = json.dumps({'sections': [{'title': '上次记录', 'content': '有 2 个批次进行中，当前状态无法确认。'}]})
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            choose.return_value = decision('operations_overview')
            response = self.ask('查看运行总览')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn('不能确认实时状态', body['introduction'])
        self.assertTrue(body['toolCalls'][0]['stale'])
        self.assertTrue(body['charts'][0]['stale'])
        self.assertIn('2020', self.synthesis.call_args.args[2]['verified_answer']['introduction'])

    def test_read_then_save_chart_uses_latest_confirmed_defaults(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.device_defaults.simulation_request', new_callable=AsyncMock) as upstream:
            choose.side_effect = [decision('test_plans', action='read'), decision('test_plans', action='save', kind='packer', minutes=2, expected_revision=2)]
            upstream.side_effect = [httpx.Response(200, json=defaults()), httpx.Response(200, json=defaults(3, 120))]
            response = self.ask('把包装默认用时改成2分钟')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(len(body['toolCalls']), 2)
        self.assertEqual(len(body['charts']), 1)
        self.assertIn('已保存 包装 · 2 分钟', body['toolCalls'][-1]['summary'])
        chart = body['charts'][0]
        position = chart['categories'].index('包装')
        self.assertEqual(chart['series'][0]['values'][position], 2)
        self.assertNotIn('usage', body)

    def test_no_snapshot_does_not_generate_a_chart_or_token_count(self):
        self.app.state.data_center_reader.data = None
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            choose.side_effect = [decision('operations_overview'), {'content': '暂无数据'}]
            response = self.ask('查看运行总览')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertNotIn('charts', body)
        self.assertNotIn('usage', body)
        self.assertEqual(body['toolCalls'][0]['summary'], '暂无可用数据')

    def test_decision_usage_requires_actual_valid_provider_counts(self):
        from app.mcp_tools.agent import request_decision
        real_client = httpx.AsyncClient
        async def run():
            for provider_usage, expected in [({'prompt_tokens': 10, 'completion_tokens': 3}, True),
                    ({'prompt_tokens': -1, 'completion_tokens': 3}, False),
                    ({'prompt_tokens': True, 'completion_tokens': 3}, False), ({}, False)]:
                def respond(request):
                    return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'done'}}], 'usage': provider_usage})
                def client(**options):
                    return real_client(transport=httpx.MockTransport(respond), **options)
                with patch('app.mcp_tools.agent.httpx.AsyncClient', side_effect=client):
                    result = await request_decision(self.settings, [], [])
                self.assertEqual('_usage' in result, expected)
        asyncio.run(run())

    def test_statistics_question_is_not_swallowed_by_legacy_overview_intent(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            choose.return_value = {'content': '请确认日期', 'tool_calls': []}
            response = self.ask('数据中心近7天统计')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mode'], 'clarification')
        choose.assert_awaited_once()

    def test_agent_creates_only_explicit_number_and_does_not_repeat(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream:
            choose.return_value = decision('test_execution', action='create', count=2, confirmed=True)
            upstream.return_value = httpx.Response(201, json={'count': 2, 'batch_ids': ['a', 'b']})
            response = self.ask('生成2个仿真演示批次')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('生成已确认', response.json()['title'])
            self.assertEqual(upstream.await_count, 1)
            self.assertEqual(choose.await_count, 1)
            upstream.reset_mock()
            response = self.ask('查看仿真运行总览')
            self.assertEqual(response.status_code, 502)
            upstream.assert_not_called()

    def test_internal_confirmation_is_derived_only_after_exact_user_authorization(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream:
            choose.return_value = decision('test_execution', action='create', count=2)
            upstream.return_value = httpx.Response(201, json={'count': 2, 'batch_ids': ['a', 'b']})
            response = self.ask('生成2个仿真演示批次')
            self.assertEqual(response.status_code, 200, response.text)
            upstream.reset_mock()
            response = self.ask('查看仿真批次')
            self.assertEqual(response.status_code, 502)
            upstream.assert_not_called()

    def test_task_creation_aliases_route_to_execution_and_keep_requested_quantity(self):
        cases = [('帮我下3个测试任务', 3), ('下发三个任务', 3), ('帮我下达两项仿真任务', 2),
                 ('安排3项测试作业', 3), ('新建3个测试任务', 3), ('帮我 下 ３ 个 测试任务', 3),
                 ('创建五十个测试任务', 50), ('下3个测试方子', 3), ('帮我下三份测试处方', 3),
                 ('下发两张模拟处方', 2), ('生成4个仿真药方', 4), ('创建一副演示方子', 1),
                 ('帮我 下 ３ 个 测试方子', 3)]
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream, patch('app.chat.ChatService.answer', side_effect=AssertionError('task must not query herbs')):
            for question, count in cases:
                with self.subTest(question=question):
                    choose.reset_mock()
                    upstream.reset_mock()
                    choose.return_value = decision('test_execution', action='create', count=count)
                    upstream.return_value = httpx.Response(201, json={'count': count, 'batch_ids': [f'b{i}' for i in range(count)]})
                    response = self.ask(question)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()['toolCalls'][0]['name'], 'test_execution')
                    self.assertEqual(response.json()['toolCalls'][0]['action'], 'create')
                    self.assertEqual(upstream.call_args.args[-1], {'count': count})
                    self.assertEqual(upstream.await_count, 1)
                    choose.assert_awaited_once()

    def test_task_creation_still_rejects_negation_methods_ranges_and_model_guesses(self):
        cases = ['不要帮我下3个测试任务', '怎么下3个测试任务？', '如果下3个测试任务会怎样',
                 '解释下3个测试任务的含义', '列出下发3个任务的示例',
                 '下3.5个测试任务', '下-3个测试任务', '下3到5个测试任务', '帮我下51个测试任务',
                 '帮我下0个测试任务', '帮我下2个测试任务', '帮我下3个测试任务再下4个任务',
                 '不要下3个测试方子', '怎么下3个测试方子？', '如果下3个测试方子会怎样',
                 '查看下发3份测试处方的示例', '下3.5个测试方子', '下-3个测试方子',
                 '下3到5个测试方子', '下51个测试方子', '下0个测试方子', '下2个测试方子',
                 '下3个测试方子再下4份测试处方']
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream, patch('app.chat.ChatService.answer', side_effect=AssertionError('task must not query herbs')):
            choose.return_value = decision('test_execution', action='create', count=3)
            for question in cases:
                with self.subTest(question=question):
                    response = self.ask(question)
                    self.assertEqual(response.status_code, 502, response.text)
            upstream.assert_not_called()
        with self.assertRaises(ToolFailure):
            authorize_write('数据中心创建3个账号', 'test_execution', {'action': 'create', 'count': 3}, [])

    def test_incomplete_and_read_only_task_questions_do_not_fall_back_to_herbs(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream, patch('app.chat.ChatService.answer', side_effect=AssertionError('task must not query herbs')):
            choose.return_value = {'content': '请说明数量', 'tool_calls': []}
            for question in ['帮我下几个测试任务', '任务现在有几个', '查看测试任务', '测试任务是什么意思',
                             '下几个测试方子', '查看测试处方', '测试方子是什么意思']:
                with self.subTest(question=question):
                    response = self.ask(question)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()['mode'], 'clarification')
            self.assertEqual(choose.await_count, 7)
            upstream.assert_not_called()

    def test_unqualified_prescriptions_stay_in_knowledge_and_cannot_authorize_creation(self):
        questions = ['下3个方子', '生成三份处方', '下3个药方', '陈皮方子的功效', '测试陈皮方子的药理作用']
        answer = {'mode': 'clarification', 'title': '请补充资料', 'introduction': '', 'sections': [], 'sources': []}
        with patch('app.chat.ChatService.answer', return_value=answer) as herbs, patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream:
            choose.return_value = decision('herbal_reference', action='ask', query='按原问题查询')
            for question in questions:
                with self.subTest(question=question):
                    response = self.ask(question)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()['toolCalls'][0]['name'], 'herbal_reference')
                    self.assertIsNone(requested_creation_count(question))
                    with self.assertRaises(ToolFailure):
                        authorize_write(question, 'test_execution', {'action': 'create', 'count': 3}, [])
            self.assertEqual(herbs.call_count, len(questions))
            self.assertEqual(choose.await_count, len(questions))
            upstream.assert_not_called()

    def test_agent_reads_before_save_and_uses_actual_revision(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.device_defaults.simulation_request', new_callable=AsyncMock) as upstream:
            choose.side_effect = [decision('test_plans', action='read'), decision('test_plans', action='save', kind='packer', minutes=2, expected_revision=2, confirmed=True)]
            upstream.side_effect = [httpx.Response(200, json=defaults()), httpx.Response(200, json=defaults(3, 120))]
            response = self.ask('把包装默认用时改成2分钟')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([t['action'] for t in response.json()['toolCalls']], ['read', 'save'])
            self.assertEqual(upstream.await_count, 2)

    def test_prompt_injection_and_invented_revision_cannot_authorize_write(self):
        args = {'action': 'save', 'kind': 'packer', 'minutes': 2, 'expected_revision': 2, 'confirmed': True}
        for question in ['如何把包装默认用时改成2分钟', '不要把包装默认用时改成2分钟', '查看测试方案', '把包装默认用时改成3分钟']:
            with self.subTest(question=question), self.assertRaises(ToolFailure):
                authorize_write(question, 'test_plans', args, [])
        with self.assertRaises(ToolFailure):
            authorize_write('把包装默认用时改成2分钟', 'test_plans', args, [('test_plans', {'action': 'read'}, {'supported': True, 'revision': 99})])

    def test_medical_tool_selection_keeps_original_question_history_and_verified_citations(self):
        answer = {'mode': 'generated', 'title': '陈皮', 'introduction': '', 'sections': [], 'sources': [{'id': 'real', 'fullText': '真实原文'}]}
        with patch('app.chat.ChatService.answer', return_value=answer) as herbs, patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            choose.return_value = decision('herbal_reference', action='ask', query='模型改写的无关问题')
            response = self.ask('陈皮的功效')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['sources'], answer['sources'])
        self.assertEqual(response.json()['toolCalls'][0]['name'], 'herbal_reference')
        choose.assert_awaited_once()
        self.assertEqual(herbs.call_args.args[0], '陈皮的功效')

    def test_unmatched_operational_language_enters_semantic_selection_without_medical_retrieval(self):
        questions = ['帮我看看最近几个方子用时 都卡在哪一步？', '这几张单怎么还没好',
                     '最近的处方做到哪了', 'What is holding up the latest jobs?']
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.chat.ChatService.answer', side_effect=AssertionError('no medical retrieval')), patch('app.main.load_reference_document', side_effect=AssertionError('no sources')):
            for question in questions:
                with self.subTest(question=question):
                    choose.return_value = {'content': '请说明具体批次', 'tool_calls': []}
                    response = self.ask(question)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()['mode'], 'clarification')
                    self.assertEqual(json.loads(choose.call_args.args[1][1]['content'])['current_question'], question)
            self.assertEqual(choose.await_count, len(questions))

    def test_router_failure_or_missing_model_never_falls_back_to_knowledge(self):
        from dataclasses import replace
        from fastapi import HTTPException
        with patch('app.chat.ChatService.answer', side_effect=AssertionError('no retrieval fallback')), patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            choose.side_effect = HTTPException(502, '工具选择失败')
            self.assertEqual(self.ask('看看最近几个方子卡哪了').status_code, 502)
            self.app.state.settings = replace(self.settings, deepseek_api_key='')
            self.assertEqual(self.ask('最近几个方子进度').status_code, 503)

    def test_recent_progress_uses_platform_stages_and_actual_processing_time_without_write(self):
        def read(settings, path, model, params=None):
            items = [{ 'id': f'b{i}', 'prescription_id': f'p{i}', 'status': 'running',
                'current_stage': 'packer', 'current_stage_name': '包装', 'progress_percent': 40,
                'temperature_c': 20, 'trace_code': f't{i}', 'created_at': i, 'sequence': i,
                'waiting_reason': '等待包装设备', 'steps': [
                    {'code': 'dispenser', 'name': '调剂', 'status': 'completed', 'elapsed_seconds': 120, 'duration_seconds': 120},
                    {'code': 'packer', 'name': '包装', 'status': 'pending', 'elapsed_seconds': 0, 'duration_seconds': 300}]} for i in range(1, 4)]
            return model.model_validate({'items': items, 'total': 3, 'offset': 0, 'limit': 200})
        with patch('app.data_center.read_simulation', side_effect=read) as upstream, patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.chat.ChatService.answer', side_effect=AssertionError('no medical retrieval')), patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as write:
            choose.side_effect = [decision('test_execution', action='progress', limit=2), {'content': '已查到'}]
            response = self.ask('帮我看看最近几个方子用时 都卡在哪一步？')
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['sources'], [])
        self.assertEqual(body['toolCalls'][0]['action'], 'progress')
        self.assertIn('包装，2 个批次，原因：等待包装设备', body['sections'][0]['content'])
        self.assertEqual([s['title'] for s in body['sections'][1:]], ['b3', 'b2'])
        content = body['sections'][1]['content']
        self.assertIn('累计实际处理：2 分钟', content)
        self.assertIn('实际处理 0 分钟；该批次配置时长 5 分钟', content)
        self.assertIn('等待包装设备', content)
        upstream.assert_called_once()
        choose.assert_awaited_once()
        write.assert_not_called()

    def test_progress_missing_times_remain_unknown_and_failed_reads_do_not_query_herbs(self):
        from fastapi import HTTPException
        item = {'id': 'old', 'prescription_id': 'p', 'status': 'queued', 'current_stage_name': '包装',
                'progress_percent': 0, 'temperature_c': 20, 'waiting_reason': None, 'trace_code': 't'}
        with patch('app.data_center.read_simulation', side_effect=lambda settings, path, model, params: model.model_validate({'items': [item], 'total': 1, 'offset': 0, 'limit': 200})) as upstream, patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.chat.ChatService.answer', side_effect=AssertionError('no retrieval fallback')):
            choose.side_effect = [decision('test_execution', action='progress', limit=5), {'content': '读取完成'}]
            response = self.ask('最近几个方子耗时')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('不能确认最近顺序', response.json()['introduction'])
            self.assertIn('无法确认', response.json()['sections'][1]['content'])
            choose.side_effect = [decision('test_execution', action='progress', limit=5)]
            upstream.side_effect = HTTPException(502, '读取失败')
            self.assertEqual(self.ask('最近几个方子耗时').status_code, 502)

    def test_recent_progress_sorts_complete_pages_and_rejects_changing_or_excessive_sets(self):
        def read(settings, path, model, params):
            offset = params['offset']
            items = [{'id': f'b{i}', 'prescription_id': f'p{i}', 'status': 'completed',
                      'progress_percent': 100, 'temperature_c': 20, 'trace_code': f't{i}',
                      'created_at': i, 'sequence': i} for i in range(offset + 1, min(offset + 201, 202))]
            return model.model_validate({'items': items, 'total': 201, 'offset': offset, 'limit': 200})
        with patch('app.data_center.read_simulation', side_effect=read) as upstream:
            result = self.tool('test_execution', {'action': 'progress', 'limit': 2})
            self.assertFalse(result.is_error, result)
            self.assertEqual([b['id'] for b in result.structured_content['items']], ['b201', 'b200'])
            self.assertEqual(upstream.call_count, 2)
            self.assertTrue(result.structured_content['ordered_by_creation'])
        def changed(settings, path, model, params):
            page = read(settings, path, model, params)
            if params['offset']:
                page.total = 202
            return page
        with patch('app.data_center.read_simulation', side_effect=changed):
            result = self.tool('test_execution', {'action': 'progress', 'limit': 2})
            self.assertTrue(result.is_error)
            self.assertIn('分页发生变化', result.content[0].text)
        with patch('app.data_center.read_simulation', side_effect=lambda settings, path, model, params: model.model_validate({'items': [], 'total': 1001, 'offset': 0, 'limit': 200})) as upstream:
            result = self.tool('test_execution', {'action': 'progress', 'limit': 2})
            self.assertTrue(result.is_error)
            upstream.assert_called_once()
        self.assertTrue(self.tool('test_execution', {'action': 'progress', 'limit': 21}).is_error)
        self.assertTrue(self.tool('test_execution', {'action': 'progress'}, token=False).is_error)

    def test_graph_limits_distinct_read_decisions_to_three(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            choose.side_effect = [decision('data_center', action='snapshot'), decision('operations_overview'),
                                  decision('test_execution', action='running'), decision('test_execution', action='status')]
            response = self.ask('综合查看当前平台运行数据')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([call['name'] for call in response.json()['toolCalls']],
                         ['data_center', 'operations_overview', 'test_execution'])
        self.assertEqual(choose.await_count, 3)

    def test_graph_finishes_on_duplicate_read_without_repeating_it(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose:
            choose.side_effect = [decision('operations_overview'), decision('operations_overview'),
                                  decision('test_execution', action='status')]
            response = self.ask('查看运行总览')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()['toolCalls']), 1)
        self.assertEqual(choose.await_count, 2)

    def test_graph_stops_on_uncertain_write_failure_without_retry(self):
        from fastapi import HTTPException
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.simulation_operations.simulation_request', new_callable=AsyncMock) as upstream:
            choose.side_effect = [decision('test_execution', action='create', count=2),
                                  decision('test_execution', action='create', count=2)]
            upstream.side_effect = HTTPException(502, '未能确认操作结果，系统不会自动重复提交。')
            response = self.ask('生成2个仿真演示批次')
        self.assertEqual(response.status_code, 502, response.text)
        self.assertIn('不会自动重复提交', response.json()['detail'])
        choose.assert_awaited_once()
        upstream.assert_awaited_once()

    def test_graph_does_not_reuse_a_prior_request_read_to_authorize_save(self):
        with patch('app.mcp_tools.agent.request_decision', new_callable=AsyncMock) as choose, patch('app.device_defaults.simulation_request', new_callable=AsyncMock) as upstream:
            choose.side_effect = [decision('test_plans', action='read'), {'content': '', 'tool_calls': []},
                                  decision('test_plans', action='save', kind='packer', minutes=2, expected_revision=2)]
            upstream.return_value = httpx.Response(200, json=defaults())
            read = self.ask('查看测试方案的默认用时')
            self.assertEqual(read.status_code, 200, read.text)
            save = self.ask('把包装默认用时改成2分钟')
        self.assertEqual(save.status_code, 502, save.text)
        self.assertIn('成功读取当前可写版本', save.json()['detail'])
        self.assertEqual(choose.await_count, 3)
        upstream.assert_awaited_once()
        self.assertEqual(upstream.call_args.args[1], 'GET')

    def test_bridge_auth_failures_are_redacted_without_login_or_retry(self):
        async def run():
            for status_code in (401, 403):
                def reject(request):
                    self.assertEqual(request.method, 'GET')
                    self.assertEqual(request.url.path, '/api/reference-document')
                    self.assertEqual(request.headers.get('X-CSRF-Protection'), '1')
                    return httpx.Response(status_code, json={'detail': 'sensitive-secret'})

                handler = Mock(side_effect=reject)
                async with httpx.AsyncClient(base_url='http://bencao.internal',
                        transport=httpx.MockTransport(handler)) as http:
                    with self.subTest(status_code=status_code), self.assertRaises(ToolFailure) as caught:
                        await BencaoClient(http).request('GET', '/api/reference-document')
                    self.assertEqual(caught.exception.status_code, status_code)
                    self.assertNotIn('sensitive-secret', str(caught.exception))
                    handler.assert_called_once()
        asyncio.run(run())
