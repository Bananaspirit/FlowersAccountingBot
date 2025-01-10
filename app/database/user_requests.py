from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from .models import User

async def ensure_user_exist(session: AsyncSession, tg_id: int):
    """Checks if the user exists."""
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def add_unknown_user(session: AsyncSession, tg_id: int, name: str):
    """Add a user if they do not exist."""
    stmt = insert(User).values(tg_id=tg_id, name=name)
    await session.execute(stmt)
    await session.commit()

async def create_first_admin(session: AsyncSession, tg_id: int):
    """Set the first admin role for the user."""
    stmt = update(User).where(User.tg_id == tg_id).values(role="admin")
    await session.execute(stmt)
    await session.commit()

async def get_user_role(session: AsyncSession, tg_id: int) -> str | None:
    """Get a user's role."""
    stmt = select(User.role).where(User.tg_id == tg_id)
    result = await session.execute(stmt)

    return result.scalar()

async def set_user_role(session: AsyncSession, tg_id: int, role: str):
    """Set a user's role."""
    stmt = update(User).where(User.tg_id == tg_id).values(role=role)
    await session.execute(stmt)
    await session.commit()

async def get_all_users_by_role(session: AsyncSession, role: str):
    """Get all users by role."""
    stmt = select(User).where(User.role == role)
    result = await session.execute(stmt)

    return result.scalars().all()

async def change_all_users_role(session: AsyncSession, role: str):
    """Change all users' role to None for a specific role."""
    stmt = update(User).where(User.role == role).values(role=None)
    await session.execute(stmt)
    await session.commit()

async def get_list_of_admins(session: AsyncSession, role: str = "admin"):
    """Get a list of admins."""
    stmt = select(User.tg_id, User.name).where(User.role == role)
    result = await session.execute(stmt)
    admins = result.fetchall()

    return {tg_id: name for tg_id, name in admins}

async def set_user_name(session: AsyncSession, tg_id: int, name: str):
    """Update a user's name."""
    stmt = update(User).where(User.tg_id == tg_id).values(name=name)
    await session.execute(stmt)
    await session.commit()