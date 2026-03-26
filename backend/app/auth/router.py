from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth import service
from app.auth.schemas import SignupRequest, TokenResponse, UserResponse, ProfileUpdateRequest
from app.auth.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    claims = await service.decode_clerk_token(token)
    user: User | None = None

    if claims is not None:
        user = await service.upsert_clerk_user(db, claims)
    else:
        user_id = service.decode_access_token(token)
        if user_id is not None:
            user = await service.get_user_by_id(db, user_id)

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not user.onboarding_completed and _is_onboarding_complete(user):
        user.onboarding_completed = True
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


def _is_onboarding_complete(user: User) -> bool:
    return all(
        [
            bool(user.display_name and user.display_name.strip()),
            user.birth_date is not None,
            bool(user.location and user.location.strip()),
            user.preferred_gender is not None,
            user.age_pref_min is not None,
            user.age_pref_max is not None,
        ]
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    existing = await service.get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await service.create_user(
        db,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        gender=body.gender,
        birth_date=body.birth_date,
        preferred_gender=body.preferred_gender,
        location=body.location,
        age_pref_min=body.age_pref_min,
        age_pref_max=body.age_pref_max,
        is_open_to_long_distance=body.is_open_to_long_distance,
    )
    token = service.create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/token", response_model=TokenResponse)
async def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await service.authenticate_user(db, form.username, form.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = service.create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    db: AsyncSession = Depends(get_db),
    form: OAuth2PasswordRequestForm = Depends(),
):
    return await login_form(form, db)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.display_name is not None:
        current_user.display_name = body.display_name
    if body.gender is not None:
        current_user.gender = body.gender
    if body.birth_date is not None:
        current_user.birth_date = body.birth_date
    if body.preferred_gender is not None:
        current_user.preferred_gender = body.preferred_gender
    if body.location is not None:
        current_user.location = body.location
    if body.age_pref_min is not None:
        current_user.age_pref_min = body.age_pref_min
    if body.age_pref_max is not None:
        current_user.age_pref_max = body.age_pref_max
    if body.is_open_to_long_distance is not None:
        current_user.is_open_to_long_distance = body.is_open_to_long_distance

    current_user.onboarding_completed = _is_onboarding_complete(current_user)

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user
