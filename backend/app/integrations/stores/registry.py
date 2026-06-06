from app.domains.stores.models import SourceConfig
from app.integrations.stores.base import StoreSourceAdapter, UnknownSourceTypeError
from app.integrations.stores.fake import FakeStoreSourceAdapter
from app.integrations.stores.static_json import StaticJsonSourceAdapter


def adapter_from_source_config(source_config: SourceConfig) -> StoreSourceAdapter:
    if source_config.source_type == "fake":
        return FakeStoreSourceAdapter()
    if source_config.source_type == "static_json":
        return StaticJsonSourceAdapter(source_config)
    raise UnknownSourceTypeError(f"Unknown source type: {source_config.source_type}")
