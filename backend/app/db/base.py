from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.domains.catalog import models as _catalog_models  # noqa: E402,F401
from app.domains.stores import models as _store_models  # noqa: E402,F401
from app.domains.users import models as _user_models  # noqa: E402,F401
