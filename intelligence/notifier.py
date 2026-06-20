"""情报通知推送。"""

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import requests

from agent.config import Config
from intelligence.models import Alert, Briefing

logger = logging.getLogger(__name__)


class Notifier:
    """多渠道通知推送器。"""

    def __init__(self, config: Config):
        self.config = config
        self.channels = config.intelligence.notify.channels

    def notify_alerts(self, alerts: List[Alert]):
        """推送一批告警。"""
        if not alerts:
            return
        for channel in self.channels:
            handler = getattr(self, f"_notify_{channel}", None)
            if handler:
                try:
                    handler(alerts)
                except Exception as exc:
                    logger.warning("通过 %s 推送告警失败: %s", channel, exc)
            else:
                logger.warning("未知通知渠道: %s", channel)

    def notify_briefing(self, briefing: Briefing):
        """推送简报。"""
        if "email" in self.channels:
            self._send_email(
                subject=briefing.title,
                body=briefing.content,
                is_html=False,
            )
        if "webhook" in self.channels:
            self._send_webhook(
                {
                    "type": "briefing",
                    "title": briefing.title,
                    "topic": briefing.topic,
                    "date": briefing.date,
                    "url": briefing.markdown_path,
                    "alert_count": len(briefing.alerts),
                }
            )
        if "console" in self.channels:
            logger.info("【简报】%s\n%s", briefing.title, briefing.content[:500])

    def _notify_console(self, alerts: List[Alert]):
        for alert in alerts:
            logger.info(
                "【情报告警】%s | 主题: %s | 相关性: %d | 新颖性: %d | 突破性: %d | %s",
                alert.article.title,
                alert.topic,
                alert.scores.relevance,
                alert.scores.novelty,
                alert.scores.breakthrough,
                alert.article.url,
            )

    def _notify_email(self, alerts: List[Alert]):
        email_config = self.config.intelligence.notify.email
        if not email_config.to or not email_config.smtp_host:
            logger.warning("邮件通知未配置收件人或 SMTP 服务器")
            return

        subject = f"研究情报告警 - {len(alerts)} 条新突破"
        body_lines = ["今日发现以下重要研究情报：", ""]
        for alert in alerts:
            body_lines.append(f"主题: {alert.topic}")
            body_lines.append(f"标题: {alert.article.title}")
            body_lines.append(f"来源: {alert.article.source}")
            body_lines.append(
                f"评分: 相关性 {alert.scores.relevance}/10, "
                f"新颖性 {alert.scores.novelty}/10, "
                f"突破性 {alert.scores.breakthrough}/10"
            )
            body_lines.append(f"链接: {alert.article.url}")
            body_lines.append("")
        body = "\n".join(body_lines)
        self._send_email(subject, body, is_html=False)

    def _send_email(self, subject: str, body: str, is_html: bool = False):
        email_config = self.config.intelligence.notify.email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = email_config.smtp_user or "research-intelligence@example.com"
        msg["To"] = ", ".join(email_config.to)
        mime_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, mime_type, "utf-8"))

        try:
            server = smtplib.SMTP(email_config.smtp_host, email_config.smtp_port, timeout=30)
            server.starttls()
            if email_config.smtp_user and email_config.smtp_password:
                server.login(email_config.smtp_user, email_config.smtp_password)
            server.sendmail(msg["From"], email_config.to, msg.as_string())
            server.quit()
            logger.info("邮件通知已发送给 %s", ", ".join(email_config.to))
        except Exception as exc:
            logger.warning("邮件发送失败: %s", exc)

    def _notify_webhook(self, alerts: List[Alert]):
        webhook_url = self.config.intelligence.notify.webhook.url
        if not webhook_url:
            logger.warning("Webhook URL 未配置")
            return

        payload = {
            "type": "alerts",
            "count": len(alerts),
            "alerts": [
                {
                    "topic": a.topic,
                    "title": a.article.title,
                    "source": a.article.source,
                    "url": a.article.url,
                    "scores": a.scores.to_dict(),
                }
                for a in alerts
            ],
        }
        self._send_webhook(payload)

    def _send_webhook(self, payload: dict):
        webhook_url = self.config.intelligence.notify.webhook.url
        if not webhook_url:
            return
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            logger.info("Webhook 通知已发送")
        except Exception as exc:
            logger.warning("Webhook 发送失败: %s", exc)
