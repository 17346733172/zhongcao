"""Presentation metadata derived only from successful, validated tool results."""

from .server import CATALOG

DEFAULT_ACTIONS = {'herbal_reference': 'search', 'data_center': 'snapshot',
                   'operations_overview': 'read', 'test_execution': 'running', 'test_plans': 'read'}
STATUS_NAMES = {'queued': '排队中', 'running': '进行中', 'paused': '已暂停', 'completed': '已完成', 'cancelled': '已取消'}


def tool_trace(name, args, data, elapsed_ms):
    action = args.get('action', DEFAULT_ACTIONS[name])
    body = data.get('data', data)
    summary = '已读取'
    if data.get('data', True) is None:
        summary = '暂无可用数据'
    elif data.get('error') or data.get('stale'):
        summary = '上次成功结果 · 当前数据过期或更新失败'
    elif name == 'test_plans':
        if action == 'save':
            changed = next(item for item in data['items'] if item['kind'] == args['kind'])
            summary = f"已保存 {changed['name']} · {changed['default_processing_seconds'] / 60:g} 分钟 · 修订号 {data['revision']}"
        else:
            summary = f"已读取 {len(data.get('items', []))} 类设备"
            if data.get('revision') is not None:
                summary += f" · 修订号 {data['revision']}"
    elif name == 'test_execution' and action == 'create':
        summary = f"已确认生成 {data['count']} 个批次"
    elif name == 'test_execution' and action in {'start', 'pause', 'status'}:
        summary = '仿真运行中' if data['clock']['running'] else '仿真已暂停'
    elif name == 'operations_overview':
        summary = f"{len(body.get('device_categories', {}))} 类设备 · {sum(body['summary']['batch_counts'].values())} 个批次"
    elif isinstance(body, dict) and 'total' in body:
        summary = f"本页 {len(body.get('items', []))} 条 · 共 {body['total']} 条"
    elif isinstance(body, dict) and 'devices' in body:
        summary = f"已读取 {len(body['devices'])} 台设备"
    elif name == 'herbal_reference' and action == 'ask':
        summary = f"{len(data.get('sources', []))} 份引用资料" if data.get('sources') else '已返回回答或资料状态'
    trace = {'name': name, 'title': CATALOG[name][1], 'action': action, 'status': 'success',
             'summary': summary, 'durationMs': round(elapsed_ms, 1), 'stale': bool(data.get('stale') or data.get('error'))}
    when = data.get('fetched_at') or data.get('synced_at')
    if when:
        trace['fetchedAt'] = when
    return trace


def chart_for_result(name, args, data):
    """Use current platform fields, never inferred quality/yield metrics."""
    body = data.get('data', data)
    if not isinstance(body, dict):
        return None
    chart = None
    if name == 'test_plans' and body.get('items'):
        chart = {'title': '设备默认每次用时', 'unit': '分钟',
                 'categories': [item['name'] for item in body['items']],
                 'series': [{'name': '当前默认用时', 'values': [item['default_processing_seconds'] / 60 for item in body['items']]}]}
    elif isinstance(body.get('summary'), dict) and body['summary'].get('batch_counts'):
        counts = body['summary']['batch_counts']
        chart = {'title': '批次状态分布', 'unit': '批', 'categories': [STATUS_NAMES[k] for k in STATUS_NAMES],
                 'series': [{'name': '批次数量', 'values': [counts[k] for k in STATUS_NAMES]}]}
    if chart:
        chart['source'] = CATALOG[name][1]
        chart['fetchedAt'] = data.get('fetched_at') or data.get('synced_at')
        chart['stale'] = bool(data.get('stale') or data.get('error'))
    return chart
