from __future__ import annotations

import json
import httpx
from typing import Optional, List
from app.config import settings
from app.core.logger import logger


class NotificationService:
    """Multi-channel notification service."""

    async def send_email(self, to: str, subject: str, body: str):
        """Send email notification."""
        if not settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping email")
            return

        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart("alternative")
            msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            async with aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                use_tls=settings.SMTP_PORT == 465,
            ) as smtp:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                await smtp.send_message(msg)

            logger.info(f"Email sent to {to}")
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")

    async def send_feishu(self, webhook_url: str, title: str, content: str):
        """Send Feishu (Lark) webhook notification."""
        try:
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": title}},
                    "elements": [{"tag": "markdown", "content": content}],
                },
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(webhook_url, json=payload)
                logger.info(f"Feishu notification sent: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to send Feishu notification: {e}")

    async def send_dingtalk(self, webhook_url: str, title: str, content: str):
        """Send DingTalk webhook notification."""
        try:
            payload = {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": f"### {title}\n{content}"},
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(webhook_url, json=payload)
                logger.info(f"DingTalk notification sent: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to send DingTalk notification: {e}")

    async def send_webhook(self, webhook_url: str, payload: dict):
        """Send generic webhook notification."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(webhook_url, json=payload)
                logger.info(f"Webhook notification sent: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")

    async def notify(
        self,
        channels: List[str],
        title: str,
        message: str,
        email_to: Optional[str] = None,
        webhook_url: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ):
        """Send notification through multiple channels."""
        for channel in channels:
            try:
                if channel == "email" and email_to:
                    await self.send_email(email_to, title, message)
                elif channel == "feishu" and webhook_url:
                    await self.send_feishu(webhook_url, title, message)
                elif channel == "dingtalk" and webhook_url:
                    await self.send_dingtalk(webhook_url, title, message)
                elif channel == "webhook" and webhook_url:
                    await self.send_webhook(
                        webhook_url,
                        {"title": title, "message": message, **(extra_data or {})},
                    )
            except Exception as e:
                logger.error(f"Failed to notify via {channel}: {e}")


notification_service = NotificationService()
