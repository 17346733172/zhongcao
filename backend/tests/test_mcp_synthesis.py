import asyncio
import json
import unittest
from unittest.mock import patch

import httpx

from app.config import Settings
from app.mcp_tools.synthesis import checked_sections, organize_answer


class SynthesisTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(deepseek_api_key='test-key', rag_enabled=False)
        self.results = [('data_center', {'action': 'question'}, {})]
        self.answer = {'mode': 'data_center', 'title': '空闲煎药锅有 2 台',
            'introduction': '上次成功读取的数据，不能确认实时状态。',
            'sections': [{'title': '设备明细', 'content': '设备编号pot-2：空闲\n设备编号pot-8：空闲'}],
            'sources': [], 'toolCalls': [{'name': 'data_center', 'stale': True}],
            'dataCenter': {'kind': 'pot', 'status': 'idle'}}

    def organize(self, answer=None, results=None, settings=None):
        return asyncio.run(organize_answer(settings or self.settings, '空闲的呢',
            results if results is not None else self.results, answer if answer is not None else self.answer))

    def test_json_request_uses_configured_model_and_only_current_evidence(self):
        requests = []
        content = json.dumps({'sections': [{'title': '查询结论', 'content': '上次记录有 2 台空闲煎药锅：pot-2、pot-8。'}]})
        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]})
        client_type = httpx.Client
        with patch('RAG.llm.httpx.Client', side_effect=lambda **kwargs:
                   client_type(transport=httpx.MockTransport(respond), **kwargs)):
            result = self.organize()
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(str(request.url), self.settings.deepseek_base_url + '/chat/completions')
        body = json.loads(request.content)
        self.assertEqual(body['model'], self.settings.deepseek_model)
        self.assertEqual(body['response_format'], {'type': 'json_object'})
        self.assertNotIn('tools', body)
        context = json.loads(body['messages'][1]['content'])
        self.assertEqual(set(context), {'current_question', 'verified_answer'})
        self.assertNotIn('test-key', json.dumps(context))
        self.assertEqual(result['sections'][0]['title'], '查询结论')
        for key in ('introduction', 'sources', 'toolCalls', 'dataCenter', 'mode'):
            self.assertEqual(result[key], self.answer[key])
        self.assertEqual(self.answer['sections'][0]['title'], '设备明细')

    def test_invalid_or_invented_content_falls_back_to_verified_results(self):
        cases = ['', '{}', '{"sections":[]}', '{"sections":[{"title":" ","content":"结果"}]}',
                 json.dumps({'sections': [{'title': '结果', 'content': '空闲有 999 台'}]}),
                 json.dumps({'sections': [{'title': '结果', 'content': '设备编号pot-28：空闲'}]}),
                 json.dumps({'sections': [{'title': '结果', 'content': '设备编号abc-2：空闲'}]}),
                 json.dumps({'sections': [{'title': '结果', 'content': '已确认[2]'}]}),
                 json.dumps({'sections': [{'title': '结果', 'content': '已确认', 'sourceIndex': 0}]}),
                 json.dumps({'sections': [{'title': '结果', 'content': '已确认'}], 'toolCalls': []})]
        with patch('app.mcp_tools.synthesis.request_json') as generate:
            for content in cases:
                with self.subTest(content=content):
                    generate.return_value = content
                    result = self.organize()
                    self.assertEqual(result['sections'], self.answer['sections'])
                    self.assertIn('AI 整理暂时未完成', result['introduction'])
                    self.assertEqual(result['toolCalls'], self.answer['toolCalls'])

    def test_knowledge_citations_and_unconfigured_rule_queries_skip_extra_model(self):
        with patch('app.mcp_tools.synthesis.request_json') as generate:
            knowledge = {**self.answer, 'sources': [{'id': 'real'}],
                'sections': [{'title': '功效', 'content': '真实原文', 'sourceIndices': [0], 'origin': 'document'}]}
            result = self.organize(knowledge, [('herbal_reference', {'action': 'ask'}, knowledge)])
            self.assertIs(result, knowledge)
            self.assertIs(self.organize(settings=Settings(rag_enabled=False)), self.answer)
            generate.assert_not_called()

    def test_oversized_evidence_is_not_truncated_or_sent(self):
        with patch('app.mcp_tools.synthesis.request_json') as generate:
            result = self.organize({**self.answer, 'sections': [{'title': '明细', 'content': 'x' * 48001}]})
            self.assertIn('AI 整理暂时未完成', result['introduction'])
            self.assertEqual(len(result['sections'][0]['content']), 48001)
            generate.assert_not_called()

    def test_structure_limits_and_unknown_numbers_in_headings_are_rejected(self):
        for payload in [
            {'sections': [{'title': '999台', 'content': '空闲'}]},
            {'sections': [{'title': '设备', 'content': '空闲'}] * 9},
            {'sections': [{'title': '设备', 'content': '空闲' * 3001}]},
            {'sections': [{'title': 2, 'content': '空闲'}]},
        ]:
            with self.subTest(payload=str(payload)[:100]), self.assertRaises(ValueError):
                checked_sections(json.dumps(payload), json.dumps(self.answer, ensure_ascii=False))
