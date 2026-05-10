import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.security import hash_password
from app.db.session import get_session
from app.models.user import User, UserRole

router = APIRouter(tags=["users"])


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.user


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserItem(BaseModel):
    user_id: str
    email: str
    role: str
    is_active: bool
    created_at: str
    model_config = {"from_attributes": True}


@router.post("/users", status_code=201, response_model=UserItem)
async def create_user(
    body: CreateUserRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> UserItem:
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered.")
    user = User(id=str(uuid.uuid4()), email=body.email, hashed_password=hash_password(body.password), role=body.role)
    session.add(user)
    await session.flush()
    return UserItem(user_id=user.id, email=user.email, role=user.role.value, is_active=user.is_active, created_at=user.created_at.isoformat())


@router.get("/users", response_model=list[UserItem])
async def list_users(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> list[UserItem]:
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    return [UserItem(user_id=u.id, email=u.email, role=u.role.value, is_active=u.is_active, created_at=u.created_at.isoformat()) for u in result.scalars()]


@router.put("/users/{user_id}", response_model=UserItem)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> UserItem:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if body.email:
        user.email = body.email
    if body.password:
        user.hashed_password = hash_password(body.password)
    if body.role:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    return UserItem(user_id=user.id, email=user.email, role=user.role.value, is_active=user.is_active, created_at=user.created_at.isoformat())


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    await session.delete(user)
