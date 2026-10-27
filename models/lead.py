from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Lead:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "new"  # new | qualified | contacted | converted

    # Step 1 – electricity bill
    monthly_bill: Optional[float] = None

    # Step 2 – contact info
    name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None

    # Step 3 – property info
    house_ownership: Optional[str] = None   # owned | rented
    roof_type: Optional[str] = None         # flat | sloped | mixed
    roof_area: Optional[float] = None       # square metres

    # Step 4 – requirements
    battery_required: Optional[bool] = None

    # Generated recommendation
    recommendation: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Lead":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
