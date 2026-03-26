import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.config import settings
from app.auth.models import User

_JWKS_CACHE: dict[str, Any] = {"keys": None, "expires_at": datetime.min.replace(tzinfo=timezone.utc)}
_JWKS_TTL_SECONDS = 300


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[uuid.UUID]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return uuid.UUID(user_id)
    except JWTError:
        return None


async def _get_clerk_jwks() -> list[dict[str, Any]]:
    jwks_url = settings.CLERK_JWKS_URL
    if not jwks_url and settings.CLERK_ISSUER:
        jwks_url = f"{settings.CLERK_ISSUER.rstrip('/')}/.well-known/jwks.json"
    if not jwks_url:
        return []
    now = datetime.now(timezone.utc)
    if _JWKS_CACHE["keys"] and now < _JWKS_CACHE["expires_at"]:
        return _JWKS_CACHE["keys"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        payload = response.json()
        keys = payload.get("keys", [])

    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["expires_at"] = now + timedelta(seconds=_JWKS_TTL_SECONDS)
    return keys


async def decode_clerk_token(token: str) -> Optional[dict[str, Any]]:
    if not settings.CLERK_ISSUER:
        return None
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            return None
        keys = await _get_clerk_jwks()
        jwk_key = next((k for k in keys if k.get("kid") == kid), None)
        if jwk_key is None:
            return None

        # Try strict decode with configured audience first.
        if settings.CLERK_AUDIENCE:
            try:
                return jwt.decode(
                    token,
                    jwk_key,
                    algorithms=["RS256"],
                    audience=settings.CLERK_AUDIENCE,
                    issuer=settings.CLERK_ISSUER,
                )
            except JWTError:
                pass

        # Fallback for setups using non-template session tokens (no audience claim).
        return jwt.decode(
            token,
            jwk_key,
            algorithms=["RS256"],
            issuer=settings.CLERK_ISSUER,
            options={"verify_aud": False},
        )
    except Exception as e:
        import traceback
        print(f"DEBUG TOKEN REJECT: {e}, kid={kid if 'kid' in locals() else 'None'}", getattr(e, "messages", ""))
        traceback.print_exc()
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_external_auth_id(db: AsyncSession, external_auth_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.external_auth_id == external_auth_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, password: str, display_name: str, **kwargs) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name,
        **kwargs,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def upsert_clerk_user(db: AsyncSession, claims: dict[str, Any]) -> Optional[User]:
    external_id = claims.get("sub")
    if not external_id:
        return None

    email = None
    email_claims = claims.get("email_addresses")
    if isinstance(email_claims, list) and email_claims:
        email = email_claims[0]
    if not email:
        email = claims.get("email")
    if not email:
        email = f"{external_id}@clerk.local"

    display_name = claims.get("name") or claims.get("given_name") or "New User"

    user = await get_user_by_external_auth_id(db, external_id)
    if user:
        if user.email != email:
            user.email = email
        if display_name and user.display_name != display_name and not user.onboarding_completed:
            user.display_name = display_name
        user.auth_provider = "clerk"
        await db.commit()
        await db.refresh(user)
        return user

    existing = await get_user_by_email(db, email)
    if existing:
        existing.external_auth_id = external_id
        existing.auth_provider = "clerk"
        await db.commit()
        await db.refresh(existing)
        return existing

    # Keep password non-null for existing schema while using Clerk as source of truth.
    user = User(
        email=email,
        hashed_password=hash_password(str(uuid.uuid4())),
        display_name=display_name,
        auth_provider="clerk",
        external_auth_id=external_id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
