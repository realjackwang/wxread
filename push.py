import os
import random
import time
import json
import requests
import logging
from config import PUSHPLUS_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN, WXPUSHER_SPT

logger = logging.getLogger(__name__)


class PushNotification:
    def __init__(self):
        self.pushplus_url = "https://www.pushplus.plus/send"
        self.telegram_url = "https://api.telegram.org/bot{}/sendMessage"
        self.headers = {'Content-Type': 'application/json'}
        # 从环境变量获取代理设置
        self.proxies = {
            'http': os.getenv('http_proxy'),
            'https': os.getenv('https_proxy')
        }
        self.wxpusher_simple_url = "https://wxpusher.zjiecode.com/api/send/message/{}/{}"
        
        # 新增：Vercel API 地址
        self.vercel_api_url = os.environ.get('VERCEL_API_URL')

    def push_pushplus(self, content, token):
        """PushPlus消息推送"""
        attempts = 5
        for attempt in range(attempts):
            try:
                response = requests.post(
                    self.pushplus_url,
                    data=json.dumps({
                        "token": token,
                        "title": "微信阅读推送...",
                        "content": content
                    }).encode('utf-8'),
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()
                logger.info("✅ PushPlus响应: %s", response.text)
                break  # 成功推送，跳出循环
            except requests.exceptions.RequestException as e:
                logger.error("❌ PushPlus推送失败: %s", e)
                if attempt < attempts - 1:  # 如果不是最后一次尝试
                    sleep_time = random.randint(180, 360)  # 随机3到6分钟
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)

    def push_telegram(self, content, bot_token, chat_id):
        """Telegram消息推送，失败时自动尝试直连"""
        url = self.telegram_url.format(bot_token)
        payload = {"chat_id": chat_id, "text": content}

        try:
            # 先尝试代理
            response = requests.post(url, json=payload, proxies=self.proxies, timeout=30)
            logger.info("✅ Telegram响应: %s", response.text)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("❌ Telegram代理发送失败: %s", e)
            try:
                # 代理失败后直连
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
            except Exception as e:
                logger.error("❌ Telegram发送失败: %s", e)
            finally:
                return False
    
    def push_wxpusher(self, content, spt):
        """WxPusher消息推送（极简方式）"""
        attempts = 5
        url = self.wxpusher_simple_url.format(spt, content)
        
        for attempt in range(attempts):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                logger.info("✅ WxPusher响应: %s", response.text)
                break
            except requests.exceptions.RequestException as e:
                logger.error("❌ WxPusher推送失败: %s", e)
                if attempt < attempts - 1:
                    sleep_time = random.randint(180, 360)
                    logger.info("将在 %d 秒后重试...", sleep_time)
                    time.sleep(sleep_time)

    # 新增: Vercel API 消息推送
    def push_vercel_api(self, source, task_name, status, message):
        """将任务状态发送到 Vercel API"""
        if not self.vercel_api_url:
            logger.error("❌ Vercel API URL未设置，无法推送任务状态。")
            return

        payload = {
            "source": source,
            "task_name": task_name,
            "status": status,
            "message": message,
            "timestamp": int(time.time())
        }

        try:
            response = requests.post(self.vercel_api_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("✅ Vercel API 推送成功: %s", response.text)
        except requests.exceptions.RequestException as e:
            logger.error("❌ Vercel API 推送失败: %s", e)


"""外部调用"""

# 统一推送接口，支持所有渠道
def push_notification(content, method, task_name, status, source="weread_script"):
    """
    一个统一的推送接口，用于向各种渠道发送通知。
    参数:
    - content: 推送消息的主体内容。
    - method: 推送渠道 (如 'pushplus', 'telegram', 'wxpusher', 'vercel_api')
    - task_name: 任务名称，用于 Vercel API。
    - status: 任务状态 ('success' 或 'failure')，用于 Vercel API。
    - source: 任务来源，用于 Vercel API。
    """
    notifier = PushNotification()

    if method == "vercel_api":
        notifier.push_vercel_api(source, task_name, status, content)
    elif method == "pushplus":
        notifier.push_pushplus(content, PUSHPLUS_TOKEN)
    elif method == "telegram":
        notifier.push_telegram(content, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    elif method == "wxpusher":
        notifier.push_wxpusher(content, WXPUSHER_SPT)
    else:
        raise ValueError("❌ 无效的通知渠道，请选择 'pushplus'、'telegram' 或 'wxpusher'")