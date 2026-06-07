"""Locust 压测脚本 - 测试聊天 API 响应时间

使用方法:
    cd backend
    pip install locust
    locust -f scripts/locustfile.py --host http://localhost:8000

然后在浏览器打开 http://localhost:8089 配置并发数和启动测试。

或使用 headless 模式直接运行:
    locust -f scripts/locustfile.py --host http://localhost:8000 \
        --headless -u 10 -r 2 --run-time 30s
"""

import json
import random

from locust import HttpUser, task, between


# 测试用的用户消息列表
TEST_MESSAGES = [
    "你好，请介绍一下你自己",
    "帮我搜索一下我的工作经历",
    "我有哪些项目经验？",
    "帮我写一段简历的自我评价",
    "Python 和 Java 的区别是什么？",
    "我的教育背景是什么？",
    "有哪些证书？",
    "帮我优化简历的技能部分",
    "前端开发需要哪些技能？",
    "如何准备面试？",
]


class ChatUser(HttpUser):
    """模拟聊天用户"""
    wait_time = between(1, 3)  # 请求间隔 1-3 秒

    @task(3)
    def chat_normal(self):
        """普通聊天请求（非流式）"""
        message = random.choice(TEST_MESSAGES)
        payload = {
            "message": message,
            "history": [],
        }
        with self.client.post(
            "/api/chat",
            json=payload,
            catch_response=True,
            stream=True,
            timeout=60,
        ) as response:
            if response.status_code == 200:
                # 读取 SSE 流直到 done
                full_text = ""
                for line in response.iter_lines():
                    line = line.decode("utf-8") if isinstance(line, bytes) else line
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "text":
                                full_text += data.get("content", "")
                            elif data.get("type") == "done":
                                break
                        except json.JSONDecodeError:
                            pass
                if full_text:
                    response.success()
                else:
                    response.failure("Empty response")
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def chat_with_history(self):
        """带历史记录的聊天请求"""
        payload = {
            "message": "继续刚才的话题",
            "history": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
            ],
        }
        with self.client.post(
            "/api/chat",
            json=payload,
            catch_response=True,
            stream=True,
            timeout=60,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def health_check(self):
        """健康检查端点"""
        with self.client.get("/api/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure("Unhealthy")
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def list_documents(self):
        """列出文档端点"""
        with self.client.get("/api/documents", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
