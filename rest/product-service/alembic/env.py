<<<<<<< HEAD
import sys, asyncio
sys.path.insert(0, "/app")
from logging.config import fileConfig
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
=======
import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from config import settings
from database import Base
import models  # noqa
>>>>>>> 7800837eda66de719ee35f3ae09b33c90f6d1ac4

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
<<<<<<< HEAD

from config import settings
from database import Base, engine  # Base is always defined in database.py
import models  # noqa — registers ORM models with Base.metadata

=======
>>>>>>> 7800837eda66de719ee35f3ae09b33c90f6d1ac4
target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()

if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_async_migrations())
