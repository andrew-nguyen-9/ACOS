from sqlalchemy.orm import Session

from backend.models.system_config import SystemConfig
from backend.repositories.base import BaseRepository


class SystemConfigRepository(BaseRepository[SystemConfig]):
    def __init__(self, session: Session) -> None:
        super().__init__(SystemConfig, session)

    def get_value(self, key: str, default: str | None = None) -> str | None:
        record = self.get(key)
        return record.value if record is not None else default

    def set_value(self, key: str, value: str, description: str | None = None) -> SystemConfig:
        record = self.get(key)
        if record is None:
            record = SystemConfig(key=key, value=value, description=description)
            self.session.add(record)
        else:
            record.value = value
            if description is not None:
                record.description = description
        self.session.flush()
        self.session.refresh(record)
        return record
