import sys, asyncio
sys.path.insert(0, "/app")
from logging.config import fileConfig
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

from config import settings
from database import Base, engine
import models  # noqa

target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()

if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_async_migrations())
