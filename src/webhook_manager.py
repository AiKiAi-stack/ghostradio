"""
Webhook 通知管理器
支持在任务完成或失败时发送外部 Webhook 通知
"""

import json
import requests
from typing import Dict, Any, Optional, List
from .logger import get_logger
from .retry_utils import network_retry

logger = get_logger("webhook")


class WebhookManager:
    """Webhook 通知管理器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.webhooks = self.config.get("webhooks", [])
        self.enabled = self.config.get("enabled", False)

    @network_retry
    def send_notification(self, event: str, data: Dict[str, Any]) -> None:
        """
        发送通知到所有配置的 Webhook

        Args:
            event: 事件类型 (job_success, job_failed)
            data: 通知数据
        """
        if not self.enabled or not self.webhooks:
            return

        payload = {
            "event": event,
            "timestamp": data.get("completed_at") or data.get("timestamp"),
            "data": data,
        }

        for webhook_url in self.webhooks:
            try:
                logger.info(f"Sending {event} notification to {webhook_url}")
                response = requests.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"Notification sent successfully to {webhook_url}")
            except Exception as e:
                logger.error(f"Failed to send notification to {webhook_url}", error=e)


def get_webhook_manager(config: Optional[Dict[str, Any]] = None) -> WebhookManager:
    """获取 Webhook 管理器实例"""
    # 这里可以实现为单例，但由于配置可能变化，直接创建也可
    return WebhookManager(config)
