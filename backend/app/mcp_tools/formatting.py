"""Render verified tool output in the existing chat answer structure."""

from datetime import datetime, timezone, timedelta
from .server import CATALOG

LABELS = {'running': '进行中', 'completed': '已完成', 'queued': '排队', 'paused': '暂停',
          'cancelled': '取消', 'busy': '使用中', 'idle': '空闲', 'fault': '故障', 'offline': '离线'}


def format_result(name, args, data):
    label = CATALOG[name][1]
    action = args.get('action', 'read')
    if name == 'herbal_reference' and action == 'ask' or name == 'data_center' and action == 'question':
        return data
    answer = {'mode': 'data_center', 'title': label, 'sources': [], 'sections': [],
              'introduction': f'已调用 MCP 工具：{label}（{action}）。'}
    when = data.get('fetched_at') or data.get('synced_at')
    if when:
        when = datetime.fromisoformat(when.replace('Z', '+00:00')).astimezone(timezone(timedelta(hours=8)))
        answer['introduction'] += f' 数据读取时间：{when:%Y-%m-%d %H:%M:%S}（北京时间）。'
    if data.get('stale') or data.get('error'):
        answer['introduction'] += ' 当前为上次成功结果，不能确认实时状态。'
    if data.get('notice'):
        answer['introduction'] += ' ' + data['notice']
    if data.get('error'):
        answer['introduction'] += ' ' + data['error']
    sections = answer['sections']
    def add(title, lines):
        sections.append({'title': title, 'content': '\n'.join(lines) or '没有符合条件的记录。'})
    if 'data' in data and data['data'] is None:
        add('读取状态', ['暂时没有成功读取的数据，请稍后重新查询。'])
        return answer
    body = data.get('data', data)
    if name == 'test_plans':
        add('设备默认每次用时', [f"{item['name']}：{item['default_processing_seconds'] / 60:g} 分钟" for item in body['items']])
        add('配置状态', [f"修订号：{body.get('revision')}",
            '保存已由平台回执确认。' if action == 'save' else '只读查询，未修改配置。',
            '仅影响后续创建的数据，已有批次保留原时长，处方显式工艺优先。'])
        return answer
    if name == 'test_execution' and action == 'progress':
        answer['title'] = '批次工序与处理用时'
        items = body['items']
        scope = '按平台创建时间倒序' if body['ordered_by_creation'] else '最近顺序未确认'
        waiting = {}
        for batch in items:
            if batch['waiting_reason'] and batch['status'] in {'running', 'queued', 'paused'}:
                key = (batch['current_stage_name'] or '未进入工序', batch['waiting_reason'])
                waiting[key] = waiting.get(key, 0) + 1
        scope_lines = [f"本次列出 {len(items)} 个批次，共 {body['total']} 个；{scope}。"]
        if waiting:
            scope_lines.append('当前等待：' + '；'.join(f'{stage}，{count} 个批次，原因：{reason}' for (stage, reason), count in waiting.items()) + '。')
        elif items:
            scope_lines.append('所列批次未返回当前等待原因，不能据此确认有卡点。')
        scope_lines.append('以下处理用时来自平台工序累计值，不含排队与暂停；没有等待起止记录时，不能判断等待多久或是否长期卡死。')
        add('查询范围', scope_lines)
        if not items:
            add('批次记录', [])
        for batch in items:
            lines = [batch_line(batch)]
            steps = batch['steps']
            if steps and all(s['elapsed_seconds'] is not None for s in steps):
                lines.append(f"累计实际处理：{sum(s['elapsed_seconds'] for s in steps) / 60:g} 分钟（不含排队/暂停）。")
            else:
                lines.append('累计实际处理用时：平台未提供完整工序计时，无法确认。')
            current = next((s for s in steps if s['code'] == batch['current_stage']), None)
            if current:
                elapsed = '未提供' if current['elapsed_seconds'] is None else f"{current['elapsed_seconds'] / 60:g} 分钟"
                planned = '未提供' if current['duration_seconds'] is None else f"{current['duration_seconds'] / 60:g} 分钟"
                lines.append(f"当前工序 {current['name']}：实际处理 {elapsed}；该批次配置时长 {planned}；设备 {current['device_id'] or '未分配'}。")
            elif not steps:
                lines.append('平台未提供工序明细，无法比较各步耗时。')
            add(batch['id'], lines)
        return answer
    if body.get('clock'):
        add('仿真状态', ['运行中' if body['clock']['running'] else '已暂停'])
    if name == 'test_execution' and action in {'create', 'start', 'pause'}:
        answer['title'] = {'create': '演示批次生成已确认', 'start': '仿真开始已确认', 'pause': '仿真暂停已确认'}[action]
        if action == 'create':
            add('生成回执', [f"生成数量：{body['count']}", '批次编号：' + '、'.join(body['batch_ids'])])
        return answer
    if body.get('summary'):
        s = body['summary']
        add('累计指标', [f"处方：{s['total_prescriptions']} 张；配发：{s['dispatched_bags']} 袋；活跃报警：{s['active_alarms']} 条",
            '批次：' + '，'.join(f'{LABELS.get(k, k)} {v}' for k, v in s['batch_counts'].items()),
            f"等待批次：{s['waiting_batches']}；每仿真小时配发：{s['bags_per_virtual_hour']:g} 袋"])
    if 'device_categories' in body:
        add('设备分类', [f"{g['name']}：{g['total']} 台（" + '，'.join(f'{LABELS.get(k, k)} {v}' for k, v in g['states'].items()) + '）'
            for g in body['device_categories'].values()])
    if 'devices' in body:
        devices = body['devices']
        add(f'设备（{len(devices)} 台，最多列出前30台）', [f"{d['id']} · {d['name']} · {LABELS.get(d['status'], d['status'])} · 关联批次 {d.get('batch_id') or '无'} · 累计利用率 {d['utilization_percent']:g}%" for d in devices[:30]])
    if 'batches' in body:
        add('进行中批次', [batch_line(b) for b in body['batches'][:30]])
    if 'items' in body:
        items = body['items']
        if name == 'test_execution' or args.get('action') == 'batch':
            lines = [batch_line(b) for b in items]
        elif name == 'data_center':
            lines = [f"{p['id']} · 处方编号 {p['external_no']} · {p['status']} · {p['doses']} 剂 · 批次 {p.get('batch_id') or '无'}" for p in items]
        else:
            lines = [p.get('text') or str(p) for p in items]
        add(f"查询结果（共 {body.get('total', len(items))} 条，偏移 {body.get('offset', 0)}）", lines)
    if name == 'data_center' and action == 'batch':
        add('批次详情', [batch_line(body)])
    if 'daily' in body:
        add('统计口径', [f"时区：{body['timezone']}；区间：{body['started_at']} 至 {body['ended_at']}",
            '历史记录不完整，缺失日期不能按零处理。' if body['partial'] else '当前区间历史记录完整。'])
        if body.get('totals'):
            add('区间合计', [totals_line(body['totals'])])
        add('每日明细', [f"{d['date']}（{d['coverage']}）：" + (totals_line(d['totals']) if d['totals'] is not None else '未留存数据') for d in body['daily']])
    if 'alarms' in body:
        add('报警（最多30条）', [f"{a['device_id']}：{a['message']}（{a['status']}）" for a in body['alarms'][:30]])
    return answer


def batch_line(b):
    return (f"{b['id']} · 关联处方 {b['prescription_id']} · {LABELS.get(b['status'], b['status'])} · "
            f"{b.get('current_stage_name') or '无当前工序'} · 进度 {b['progress_percent']:g}% · "
            f"等待原因：{b.get('waiting_reason') or '无'} · 追溯码 {b['trace_code']}")


def totals_line(t):
    return f"新增处方 {t['prescriptions']}，新增批次 {t['batches']}，完成批次 {t['completed']}，配发袋数 {t['dispatched_bags']}，新增报警 {t['alarms']}"
