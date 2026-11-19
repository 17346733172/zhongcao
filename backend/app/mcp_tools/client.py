"""Internal API bridge using the current page's authenticated session."""

import httpx


class ToolFailure(Exception):
    def __init__(self, detail, status_code=502):
        super().__init__(detail)
        self.status_code = status_code


class BencaoClient:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http
        self.server_timing = None

    async def request(self, method, route, *, params=None, body=None):
        try:
            response = await self.http.request(method, route, params=params,
                headers={'X-CSRF-Protection': '1'}, **({'json': body} if body is not None else {}))
            if response.headers.get('server-timing'):
                self.server_timing = response.headers['server-timing']
            if response.status_code in (401, 403):
                raise ToolFailure('当前登录已失效或无权限，请重新登录；不会自动重试操作。', response.status_code)
            if not response.is_success:
                # Only return the local API's vetted error, never transport exceptions.
                detail = response.json().get('detail')
                raise ToolFailure(detail if isinstance(detail, str) else '业务接口拒绝请求，请核对参数。', response.status_code)
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise ToolFailure('无法确认本草接口结果，请检查服务并重新读取状态；不会自动重复提交。') from None
