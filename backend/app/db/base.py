from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.domains.users import models as _user_models  # noqa: E402,F401
