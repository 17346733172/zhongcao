"""External stdio entry point: python -m app.mcp_tools (or --env-file PATH)."""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.stdio import stdio_server
from .client import BencaoClient, validate_base_url
from .server import create_server


async def serve():
    parser = argparse.ArgumentParser(description='本草五模块 MCP（stdio）')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    if args.env_file:
        if not args.env_file.is_file():
            raise ValueError('找不到指定的 MCP 环境配置文件。')
        load_dotenv(args.env_file, override=False)
    url = validate_base_url(os.environ.get('BENCAO_MCP_API_URL', 'http://127.0.0.1:8000'))
    username, password = os.environ.get('BENCAO_MCP_USERNAME'), os.environ.get('BENCAO_MCP_PASSWORD')
    if not username or not password:
        raise ValueError('请在环境变量或 --env-file 中设置 BENCAO_MCP_USERNAME / BENCAO_MCP_PASSWORD。')
    # HTTP logs can include paths / inputs. stdout is reserved for JSON-RPC only.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    async with httpx.AsyncClient(base_url=url, timeout=190, trust_env=False, follow_redirects=False) as http:
        server = create_server(BencaoClient(http, username, password))
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())


if __name__ == '__main__':
    try:
        asyncio.run(serve())
    except (ValueError, OSError):
        print('MCP 启动失败：请检查环境文件、服务入口及账号环境变量。', file=sys.stderr)
        raise SystemExit(1) from None
