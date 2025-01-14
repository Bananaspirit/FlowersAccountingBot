from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from .models import User

async def ensure_user_exist(session: AsyncSession, tg_id: int):
    """Checks if the user exists."""
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def add_unknown_user(session: AsyncSession, tg_id: int, first_name: str, full_name: str):
    """Add a user if they do not exist."""
    await session.execute(
        insert(User)
        .values(
            tg_id=tg_id,
            first_name=first_name,
            full_name=full_name
        )
    )
    await session.commit()

async def get_user_info(session: AsyncSession, tg_id: int):
    result = await session.execute(
        select(User)
        .where(User.tg_id == tg_id)
    )
    return result.scalars().first()

async def update_user_names(session: AsyncSession, tg_id: int, first_name: str, full_name: str):
    """Update a user's name."""
    await session.execute(
        update(User)
        .where(User.tg_id == tg_id)
        .values(
            first_name=first_name,
            full_name=full_name
        )
    )
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
    stmt = select(User.tg_id, User.full_name).where(User.role == role)
    result = await session.execute(stmt)
    admins = result.fetchall()

    return {tg_id: full_name for tg_id, full_name in admins}