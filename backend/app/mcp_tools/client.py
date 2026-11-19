"""Authenticated API bridge. No credentials, URLs or arbitrary routes in tool inputs."""

import asyncio
from urllib.parse import urlsplit

import httpx


class ToolFailure(Exception):
    def __init__(self, detail, status_code=502):
        super().__init__(detail)
        self.status_code = status_code


class BencaoClient:
    def __init__(self, http: httpx.AsyncClient, username=None, password=None):
        self.http = http
        self.username, self.password = username, password
        self.authenticated = username is None
        self.login_lock = asyncio.Lock()
        self.server_timing = None

    async def request(self, method, route, *, params=None, body=None):
        try:
            async with self.login_lock:
                if not self.authenticated:
                    response = await self.http.post('/api/auth/login',
                        headers={'X-CSRF-Protection': '1'},
                        json={'username': self.username, 'password': self.password})
                    if response.status_code != 200:
                        raise ToolFailure('MCP 登录失败，请检查账号、密码、账号状态或登录限流。')
                    self.authenticated = True
            response = await self.http.request(method, route, params=params,
                headers={'X-CSRF-Protection': '1'}, **({'json': body} if body is not None else {}))
            if response.headers.get('server-timing'):
                self.server_timing = response.headers['server-timing']
            if response.status_code in (401, 403):
                raise ToolFailure('当前登录已失效或无权限，请重新连接 MCP；不会自动重试操作。', response.status_code)
            if not response.is_success:
                # Only return the local API's vetted error, never transport exceptions.
                detail = response.json().get('detail')
                raise ToolFailure(detail if isinstance(detail, str) else '业务接口拒绝请求，请核对参数。', response.status_code)
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise ToolFailure('无法确认本草接口结果，请检查服务并重新读取状态；不会自动重复提交。') from None


def validate_base_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'', '/'}):
        raise ValueError('BENCAO_MCP_API_URL 必须是无凭据、路径和查询参数的 HTTP(S) 服务入口。')
    if parsed.scheme == 'http' and parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise ValueError('远程本草接口必须使用 HTTPS。')
    return url.rstrip('/')
