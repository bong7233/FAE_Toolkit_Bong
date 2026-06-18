"""IO snapshot data model."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from fae_toolkit.protocols.io import map as io_map


@dataclass(slots=True)
class IoSnapshot:
    """A point-in-time view of all IO channels."""

    di: list[bool]
    do: list[bool]
    ai: list[float]
    timestamp: float = field(default_factory=time.time)

    @property
    def interlock_ok(self) -> bool:
        """Safe to actuate: E-stop healthy and safety area clear."""
        return self.di[io_map.DI_ES] and self.di[io_map.DI_AREA_CLEAR]

    def di_named(self) -> dict[str, bool]:
        return {io_map.DI_NAMES[i]: v for i, v in enumerate(self.di)}

    def do_named(self) -> dict[str, bool]:
        return {io_map.DO_NAMES[i]: v for i, v in enumerate(self.do)}

    def ai_named(self) -> dict[str, tuple[float, str]]:
        return {io_map.AI_NAMES[i]: (v, io_map.AI_UNITS[i]) for i, v in enumerate(self.ai)}

    def active_inputs(self) -> list[str]:
        return [io_map.DI_NAMES[i] for i, v in enumerate(self.di) if v]

    def active_outputs(self) -> list[str]:
        return [io_map.DO_NAMES[i] for i, v in enumerate(self.do) if v]
