"""Frontend-independent UTC data models."""
from dataclasses import dataclass, field
from datetime import datetime, timezone

UTC = timezone.utc

@dataclass(frozen=True)
class Session:
    name: str
    start: datetime | None

@dataclass(frozen=True)
class GrandPrix:
    round: int
    name: str
    circuit_id: str
    circuit: str
    location: str
    latitude: float | None
    longitude: float | None
    race_date: str
    sessions: tuple[Session, ...]
    warnings: tuple[str, ...] = ()

    @property
    def race_start(self):
        return next((s.start for s in self.sessions if s.name == 'RACE'), None)


def next_gp_index(races, now=None):
    now = now or datetime.now(UTC)
    # A weekend remains selected until the race starts, even after FP1.
    for i, race in enumerate(races):
        end = race.race_start or datetime.fromisoformat(race.race_date).replace(
            hour=23, minute=59, second=59, tzinfo=UTC)
        if end > now:
            return i
    return len(races) - 1

@dataclass(frozen=True)
class Forecast:
    time: datetime
    values: dict = field(default_factory=dict)
