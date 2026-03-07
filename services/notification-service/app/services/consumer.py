import json
from datetime import datetime, timezone

import aio_pika
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models.notification import NotificationLog, NotificationType, NotificationStatus
from app.services.sender import send_email, send_sms
from app.services.templates import render_template


async def handle_user_registered(payload: dict, db: AsyncSession):
    subject, body = render_template("welcome", {
        "full_name": payload.get("full_name", "there"),
    })
    success = await send_email(payload["email"], subject, body)

    log = NotificationLog(
        user_id=payload["user_id"],
        type=NotificationType.EMAIL,
        status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
        recipient=payload["email"],
        subject=subject,
        template="welcome",
        payload=payload,
        sent_at=datetime.now(timezone.utc) if success else None,
    )
    db.add(log)
    await db.commit()


async def handle_password_reset(payload: dict, db: AsyncSession):
    subject, body = render_template("password_reset", {
        "reset_token": payload.get("reset_token", ""),
    })
    success = await send_email(payload["email"], subject, body)

    log = NotificationLog(
        user_id=payload.get("user_id", "unknown"),
        type=NotificationType.EMAIL,
        status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
        recipient=payload["email"],
        subject=subject,
        template="password_reset",
        payload=payload,
        sent_at=datetime.now(timezone.utc) if success else None,
    )
    db.add(log)
    await db.commit()


async def handle_file_uploaded(payload: dict, db: AsyncSession):
    subject, body = render_template("file_uploaded", {
        "filename": payload.get("filename", "unknown"),
        "file_size": payload.get("file_size", "unknown"),
    })
    success = await send_email(payload["email"], subject, body)

    log = NotificationLog(
        user_id=payload["user_id"],
        type=NotificationType.EMAIL,
        status=NotificationStatus.SENT if success else NotificationStatus.FAILED,
        recipient=payload["email"],
        subject=subject,
        template="file_uploaded",
        payload=payload,
        sent_at=datetime.now(timezone.utc) if success else None,
    )
    db.add(log)
    await db.commit()


EVENT_HANDLERS = {
    "user.registered": handle_user_registered,
    "user.password_reset": handle_password_reset,
    "file.uploaded": handle_file_uploaded,
}


async def start_consumer():
    """Start consuming messages from RabbitMQ"""
    logger.info("Starting RabbitMQ consumer...")
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        # Declare exchanges to consume from
        user_exchange = await channel.declare_exchange(
            "user_events", aio_pika.ExchangeType.TOPIC, durable=True
        )
        file_exchange = await channel.declare_exchange(
            "file_events", aio_pika.ExchangeType.TOPIC, durable=True
        )

        # Declare and bind notification queue
        queue = await channel.declare_queue("notification_queue", durable=True)
        await queue.bind(user_exchange, routing_key="user.*")
        await queue.bind(file_exchange, routing_key="file.*")

        logger.info("Notification consumer ready, waiting for events...")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        payload = json.loads(message.body.decode())
                        event_type = payload.get("event") or message.routing_key
                        handler = EVENT_HANDLERS.get(event_type)

                        if handler:
                            async with AsyncSessionLocal() as db:
                                await handler(payload, db)
                        else:
                            logger.warning(f"No handler for event: {event_type}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
