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
import os, sys
sys.path.insert(0, str(__file__).replace("/alembic/env.py",""))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
>>>>>>> 7800837eda66de719ee35f3ae09b33c90f6d1ac4

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

<<<<<<< HEAD
from config import settings
from database import Base, engine  # Base is always defined in database.py
import models  # noqa — registers ORM models with Base.metadata

target_metadata = Base.metadata
=======
# import Base from the service
from database import engine
try:
    from models import Base
    from _shared.base import Base as SharedBase
    target_metadata = Base.metadata
except Exception:
    from _shared.base import Base
    target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=os.environ.get("DATABASE_URL",""), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
>>>>>>> 7800837eda66de719ee35f3ae09b33c90f6d1ac4

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
<<<<<<< HEAD
    engine = create_async_engine(settings.database_url)
=======
>>>>>>> 7800837eda66de719ee35f3ae09b33c90f6d1ac4
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()

<<<<<<< HEAD
if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_async_migrations())
=======
def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
>>>>>>> 7800837eda66de719ee35f3ae09b33c90f6d1ac4
