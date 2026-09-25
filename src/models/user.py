from dataclasses import dataclass, field


@dataclass
class User:
    id: str
    name: str
    email: str
