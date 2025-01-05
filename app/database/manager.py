import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker
from .models import UserBase, DataBase
from datetime import datetime
from contextlib import asynccontextmanager

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
        self.active_sessions = {"user": [], "data": []}
        self._data_engines = {}
    
    # async def get_user_session(self):
    #     session = self.user_sessionmaker()
    #     self.active_sessions["user"].append(session)
    #     return session
    @asynccontextmanager
    async def get_user_session(self):
        async with self.user_sessionmaker() as session:
            try:
                yield session
            finally:
                await session.close()

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

    def get_data_db_path(self,) -> str:
        """Generates the path to the database for the specified year and month."""
        months = {1: "January",
              2: "February",
              3: "March",
              4: "April",
              5: "May",
              6: "June",
              7: "July",
              8: "August",
              9: "September",
              10: "October",
              11: "November",
              12: "December"
              }
        now = datetime.now()
        year = str(now.year)
        month = f"{months[now.month]}"

        month_dir = os.path.join(self.data_base_dir, year, month)
        os.makedirs(month_dir, exist_ok=True)

        return month_dir

    # def get_data_engine(self):
    #     """Creates an engine for the specified year/month database."""

    #     data_db_path = self.get_data_db_path()

    #     return create_async_engine(f"sqlite+aiosqlite:///{data_db_path}/data.sqlite3")
    def get_data_engine(self):
        data_db_path = self.get_data_db_path()
        if data_db_path not in self._data_engines:
            self._data_engines[data_db_path] = create_async_engine(f"sqlite+aiosqlite:///{data_db_path}/data.sqlite3")
        return self._data_engines[data_db_path]

    async def create_data_db(self):
        """Creates the database for the specified year and month."""

        engine = self.get_data_engine()
        async with engine.begin() as conn:
            await conn.run_sync(DataBase.metadata.create_all)

        return engine

    # async def get_data_sessionmaker(self):
    #     """Returns a sessionmaker for the specified year/month database."""

    #     engine = self.get_data_engine()
    #     data_sessionmaker: async_sessionmaker[AsyncSession] = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    #     return data_sessionmaker
    async def get_data_sessionmaker(self):
        engine = self.get_data_engine()
        if not hasattr(self, "_data_sessionmaker"):
            self._data_sessionmaker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        return self._data_sessionmaker
    
    async def get_data_session(self):
        session_instance = await self.get_data_sessionmaker()
        session = session_instance()
        self.active_sessions["data"].append(session)
        return session
    
    async def drop_data_db(self):
        """Deletes the data database."""

        async with self.get_data_engine().begin() as conn:
            await conn.run_sync(DataBase.metadata.drop_all)