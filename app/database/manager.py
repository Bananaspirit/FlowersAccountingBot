import os
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker
from .models import UserBase, DataBase
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from . import data_requests as drq

class DatabaseManager:
    def __init__(self, user_base_dir: str, data_base_dir: str):
        # Path to the fixed user database
        self.user_db_path = user_base_dir

        # Directory where year/month databases are stored
        self.data_base_dir = data_base_dir

        # Initialize the user database engine and sessionmaker
        self.user_engine = create_async_engine(f"sqlite+aiosqlite:///{user_base_dir}/users.sqlite3")
        self.user_sessionmaker: async_sessionmaker[AsyncSession] = sessionmaker(
            bind=self.user_engine, class_=AsyncSession, expire_on_commit=False
        )
        self.current_data_db_path = None
        self.active_sessions = {"user": [], "data": []}
    
    async def get_user_session(self):
        session = self.user_sessionmaker()
        self.active_sessions["user"].append(session)
        return session

    async def cleanup_sessions(self):
        """Close all active sessions."""

        while self.active_sessions["user"]:
            session = self.active_sessions["user"].pop()
            await session.close()
        
        while self.active_sessions["data"]:
            session = self.active_sessions["data"].pop()
            await session.close()

    async def create_user_db(self):
        """Creates the user database if it does not exist."""

        async with self.user_engine.begin() as conn:
            await conn.run_sync(UserBase.metadata.create_all)

    async def drop_user_db(self):
        """Deletes the user database."""

        async with self.user_engine.begin() as conn:
            await conn.run_sync(UserBase.metadata.drop_all)

    def get_data_db_path(self, date = datetime.now(), previous_month = False, mkdir = True) -> str:
        """Generates the path to the database for the specified year and month."""
        
        if not previous_month:
            year = str(date.year)
            month = f"{date.strftime('%B')}"

            month_dir = os.path.join(self.data_base_dir, year, month)
            if mkdir:
                os.makedirs(month_dir, exist_ok=True)
        else:
            first_day_of_current_month = datetime(year=date.year, month=date.month, day=1)
            last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)

            year = str(last_day_of_previous_month.year)
            month = f"{last_day_of_previous_month.strftime('%B')}"

            month_dir = os.path.join(self.data_base_dir, year, month)

        return os.path.join(month_dir, "data.sqlite3")
    
    def database_exists(self, db_path):
        """Check if a database file exists."""
        return os.path.exists(db_path)

    def create_data_engine(self, db_path: str):
        """Creates an engine for a given database path."""
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        return engine

    async def create_data_db(self, engine: AsyncEngine):
        """Creates tables in the specified database."""

        async with engine.begin() as conn:
            await conn.run_sync(DataBase.metadata.create_all)
    
    async def migrate_to_new_month(self):
        """Handles database migration when a new month begins."""

        new_data_db_path = self.get_data_db_path()
        prev_data_db_path = self.get_data_db_path(previous_month=True)

        # Migration logic
        if not self.database_exists(new_data_db_path):
            new_engine = self.create_data_engine(new_data_db_path)
            await self.create_data_db(new_engine)

            if self.database_exists(prev_data_db_path):
                old_engine = self.create_data_engine(prev_data_db_path)
                async with old_engine.connect() as old_conn, new_engine.connect() as new_conn:

                    if not await drq.is_migrations_ready(new_conn):
                        # async with new_conn.begin() as trans: # rollback в случае неудачи
                        result = await drq.migrate_data(old_conn, new_conn)
                        if result:
                            await drq.mark_migrations_is_ready(new_conn)

            self.current_data_db_path = new_data_db_path
        else:
            self.current_data_db_path = new_data_db_path

    async def get_data_sessionmaker(self):
        """Returns a sessionmaker for the specified year/month database."""
        await self.migrate_to_new_month()

        engine = self.create_data_engine(self.current_data_db_path)
        data_sessionmaker: async_sessionmaker[AsyncSession] = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        return data_sessionmaker
    
    async def get_data_session(self):
        session_instance = await self.get_data_sessionmaker()
        session = session_instance()
        self.active_sessions["data"].append(session)
        return session
    
    async def drop_data_db(self):
        """Deletes the current data database."""
        new_data_db_path = self.get_data_db_path()
        if self.database_exists(new_data_db_path):
            engine = self.create_data_engine(new_data_db_path)
            async with engine.begin() as conn:
                await conn.run_sync(DataBase.metadata.drop_all)