import asyncio
import random
import time
from typing import Optional

import botpy
from aiohttp import web
from botpy.types.message import Message

from monitor.config import QQ_OFFICIAL_APPID, QQ_OFFICIAL_SECRET, QQ_HTTP_PORT

SESSION_TTL = 3600  # 会话有效期（秒）


class ActiveUserRegistry:
    """管理活跃用户会话，含 TTL 过期清理（读时触发）"""

    def __init__(self, ttl: int = SESSION_TTL):
        self._sessions: dict[str, tuple[str, float]] = {}
        self._ttl = ttl

    def update(self, user_openid: str, msg_id: str) -> None:
        self._sessions[user_openid] = (msg_id, time.time())

    def get_msg_id(self, user_openid: str) -> Optional[str]:
        self._cleanup()
        entry = self._sessions.get(user_openid)
        return entry[0] if entry else None

    def has_user(self, user_openid: str) -> bool:
        return self.get_msg_id(user_openid) is not None

    def remove(self, user_openid: str) -> None:
        self._sessions.pop(user_openid, None)

    def active_count(self) -> int:
        self._cleanup()
        return len(self._sessions)

    def active_openids(self) -> list[str]:
        self._cleanup()
        return list(self._sessions.keys())

    def _cleanup(self) -> None:
        now = time.time()
        stale = [k for k, (_, ts) in self._sessions.items() if now - ts > self._ttl]
        for k in stale:
            del self._sessions[k]


class MyClient(botpy.Client):
    def __init__(self, intents, registry: ActiveUserRegistry):
        super().__init__(intents=intents)
        self._registry = registry
        self._msg_seq = int(time.time()) % 1_000_000 + random.randint(1000, 9999)

    def _next_seq(self) -> int:
        self._msg_seq += 1
        return self._msg_seq

    async def on_ready(self):
        print(f"### 机器人已启动: {self.robot.name}")

    async def send_alert(self, user_openid: str, content: str) -> bool:
        """发送告警消息给指定用户"""
        msg_id = self._registry.get_msg_id(user_openid)
        if not msg_id:
            print(f"### 无法发送告警，用户 {user_openid} 未激活")
            return False
        try:
            result = await self.api.post_c2c_message(
                user_openid=user_openid,
                msg_id=msg_id,
                msg_seq=self._next_seq(),
                content=content,
            )
            print(f"### 告警发送成功: {result}")
            return True
        except Exception as e:
            print(f"### 告警发送失败: {e}")
            return False

    async def on_c2c_message_create(self, message: Message):
        """处理单聊消息"""
        print(f"### 收到单聊消息: {message.content}")
        print(f"### user_openid: {message.author.user_openid}")
        print(f"### msg_id: {message.id}")

        user_openid = message.author.user_openid
        self._registry.update(user_openid, message.id)
        print(f"### 已记录用户会话: {user_openid}")

        if "开启监控" in message.content or "启动监控" in message.content:
            reply = "✅ 监控已启动！检测到异常时会发送告警。"
        elif "关闭监控" in message.content or "停止监控" in message.content:
            self._registry.remove(user_openid)
            reply = "⏹️ 监控已停止。"
        elif "状态" in message.content:
            reply = f"📊 当前状态：机器人运行中\n已激活用户数: {self._registry.active_count()}"
        else:
            reply = "收到你的消息啦！发送「开启监控」启动安防监控告警。"

        try:
            result = await self.api.post_c2c_message(
                user_openid=user_openid,
                msg_id=message.id,
                content=reply,
            )
            print(f"### 发送成功: {result}")
        except Exception as e:
            print(f"### 发送失败: {e}")


def make_http_app(bot_client: MyClient) -> web.Application:
    """构建 aiohttp 应用，通过 app 对象传递 bot_client，避免全局变量"""
    app = web.Application()
    app["bot_client"] = bot_client

    async def handle_alert(request: web.Request) -> web.Response:
        try:
            data = await request.json()
            user_openid = data.get("user_openid")
            content = data.get("content")
            if not user_openid or not content:
                return web.json_response({"success": False, "error": "缺少 user_openid 或 content 参数"})
            client: MyClient = request.app["bot_client"]
            success = await client.send_alert(user_openid, content)
            return web.json_response({
                "success": success,
                "message": "告警已发送" if success else "告警发送失败",
            })
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)})

    async def handle_status(request: web.Request) -> web.Response:
        registry: ActiveUserRegistry = request.app["bot_client"]._registry
        return web.json_response({
            "active_users": registry.active_openids(),
            "active_count": registry.active_count(),
        })

    app.router.add_post("/alert", handle_alert)
    app.router.add_get("/status", handle_status)
    return app


async def run_bot_with_http():
    """同时运行机器人和 HTTP 服务"""
    registry = ActiveUserRegistry()
    intents = botpy.Intents.all()
    client = MyClient(intents=intents, registry=registry)

    app = make_http_app(client)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", QQ_HTTP_PORT)
    await site.start()
    print(f"### HTTP 服务已启动: http://127.0.0.1:{QQ_HTTP_PORT}")

    await client.start(appid=QQ_OFFICIAL_APPID, secret=QQ_OFFICIAL_SECRET)
