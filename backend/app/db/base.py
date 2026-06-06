from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.domains.catalog import models as _catalog_models  # noqa: E402,F401
from app.domains.fx import models as _fx_models  # noqa: E402,F401
from app.domains.notifications import models as _notification_models  # noqa: E402,F401
from app.domains.offers import models as _offer_models  # noqa: E402,F401
from app.domains.shopping_requests import models as _shopping_request_models  # noqa: E402,F401
from app.domains.stores import models as _store_models  # noqa: E402,F401
from app.domains.users import models as _user_models  # noqa: E402,F401
from app.domains.watchlists import models as _watchlist_models  # noqa: E402,F401
