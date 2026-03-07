import json
import aio_pika
from loguru import logger

from app.core.config import settings

_connection = None
_channel = None


async def get_channel():
    global _connection, _channel
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        _channel = await _connection.channel()
        # Declare exchanges
        await _channel.declare_exchange("user_events", aio_pika.ExchangeType.TOPIC, durable=True)
    return _channel


async def publish_event(routing_key: str, payload: dict):
    """Publish an event to the user_events exchange"""
    try:
        channel = await get_channel()
        exchange = await channel.declare_exchange("user_events", aio_pika.ExchangeType.TOPIC, durable=True)
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=routing_key)
        logger.info(f"Published event: {routing_key}")
    except Exception as e:
        logger.error(f"Failed to publish event {routing_key}: {e}")


# ── Specific event publishers ─────────────────────────────────────────────────

async def publish_user_registered(user_id: str, email: str, full_name: str):
    await publish_event("user.registered", {
        "user_id": user_id,
        "email": email,
        "full_name": full_name,
        "event": "user.registered",
    })


async def publish_password_reset_requested(email: str, reset_token: str):
    await publish_event("user.password_reset", {
        "email": email,
        "reset_token": reset_token,
        "event": "user.password_reset",
    })
