from dataclasses import dataclass, field
from typing import List


@dataclass
class Project:
    id: str
    name: str
    description: str
    owner_id: str
    member_ids: List[str] = field(default_factory=list)
