import botpy
from botpy.types.message import Message
import asyncio
import random
import time
import os
from dotenv import load_dotenv
from aiohttp import web

# 加载环境变量
load_dotenv()

# 从环境变量读取敏感信息
appid = os.getenv("QQ_OFFICIAL_APPID")
secret = os.getenv("QQ_OFFICIAL_SECRET")

# 存储活跃的用户会话信息（用于被动回复）
active_users = {}
# HTTP 服务端口
HTTP_PORT = 8083
# 全局消息序列号计数器（用于避免去重，必须全局唯一）
# 使用随机数初始化，避免重启后重复
msg_seq_counter = int(time.time()) % 1000000 + random.randint(1000, 9999)

class MyClient(botpy.Client):
    async def on_ready(self):
        print(f"### 机器人已启动: {self.robot.name}")

    def get_next_msg_seq(self):
        """获取下一个 msg_seq，确保全局唯一性"""
        global msg_seq_counter
        msg_seq_counter += 1
        return msg_seq_counter

    async def send_alert(self, user_openid, content):
        """直接发送告警消息"""
        if user_openid and user_openid in active_users:
            # 使用最近的 msg_id 进行被动回复
            msg_id = active_users[user_openid]
            # 获取唯一的 msg_seq（全局唯一）
            msg_seq = self.get_next_msg_seq()
            try:
                result = await self.api.post_c2c_message(
                    user_openid=user_openid,
                    msg_id=msg_id,
                    msg_seq=msg_seq,
                    content=content
                )
                print(f"### 告警发送成功: {result}")
                return True
            except Exception as e:
                print(f"### 告警发送失败: {e}")
                return False
        else:
            print(f"### 无法发送告警，用户 {user_openid} 未激活")
            return False
        
    async def on_c2c_message_create(self, message: Message):
        """处理单聊消息"""
        print(f"### 收到单聊消息: {message.content}")
        print(f"### user_openid: {message.author.user_openid}")
        print(f"### msg_id: {message.id}")
        
        # 保存用户会话信息
        user_openid = message.author.user_openid
        active_users[user_openid] = message.id
        print(f"### 已记录用户会话: {user_openid}")
        
        # 处理命令
        if "开启监控" in message.content or "启动监控" in message.content:
            reply = "✅ 监控已启动！检测到异常时会发送告警。"
        elif "关闭监控" in message.content or "停止监控" in message.content:
            if user_openid in active_users:
                del active_users[user_openid]
            reply = "⏹️ 监控已停止。"
        elif "状态" in message.content:
            reply = f"📊 当前状态：机器人运行中\n已激活用户数: {len(active_users)}"
        else:
            reply = "收到你的消息啦！发送「开启监控」启动安防监控告警。"
        
        try:
            result = await self.api.post_c2c_message(
                user_openid=user_openid, 
                msg_id=message.id,
                content=reply
            )
            print(f"### 发送成功: {result}")
        except Exception as e:
            print(f"### 发送失败: {e}")


async def send_alert_to_qq(user_openid, content):
    """供 img_detect.py 调用的函数，直接发送告警"""
    try:
        # 获取全局 client 实例发送消息
        # 注意：需要在 main 中设置全局 client
        if 'global_client' in globals() and global_client:
            return await global_client.send_alert(user_openid, content)
        else:
            print("### 机器人客户端未就绪")
            return False
    except Exception as e:
        print(f"### 发送告警失败: {e}")
        return False


# ===================== HTTP 服务 =====================
async def handle_alert(request):
    """处理来自 img_detect.py 的告警请求"""
    try:
        data = await request.json()
        user_openid = data.get("user_openid")
        content = data.get("content")
        
        if not user_openid or not content:
            return web.json_response({
                "success": False, 
                "error": "缺少 user_openid 或 content 参数"
            })
        
        # 直接发送告警
        success = await send_alert_to_qq(user_openid, content)
        
        return web.json_response({
            "success": success,
            "message": "告警已发送" if success else "告警发送失败"
        })
    except Exception as e:
        return web.json_response({
            "success": False,
            "error": str(e)
        })


async def handle_status(request):
    """查询机器人状态"""
    return web.json_response({
        "active_users": list(active_users.keys()),
        "active_count": len(active_users)
    })


async def start_http_server():
    """启动 HTTP 服务"""
    app = web.Application()
    app.router.add_post('/alert', handle_alert)
    app.router.add_get('/status', handle_status)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', HTTP_PORT)
    await site.start()
    print(f"### HTTP 服务已启动: http://127.0.0.1:{HTTP_PORT}")


# 全局 client 实例
global_client = None

# ===================== 主程序 =====================
async def main():
    """同时运行机器人和 HTTP 服务"""
    global global_client
    
    # 启动 HTTP 服务
    await start_http_server()
    
    # 启动机器人
    intents = botpy.Intents.all()
    global_client = MyClient(intents=intents)
    await global_client.start(appid=appid, secret=secret)


if __name__ == "__main__":
    asyncio.run(main())
