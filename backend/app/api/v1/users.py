from fastapi import APIRouter

from app.api.deps import CurrentUserDep
from app.domains.users.models import User
from app.domains.users.schemas import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUserDep) -> User:
    return current_user
