"""
Maintenance policies compared in this project.

RTF  Run-to-failure: corrective maintenance only.
TBM  Time-based PM: overhaul after every `pm_interval_h` operating hours.
CBM  Condition-based: inspect every `inspection_h` hours; request PM when the
     ESTIMATED health is below `threshold`. The crew serves requests first come,
     first served.
RBM  Risk-based: same inspections, but each machine gets
     risk = P(failure before next inspection) x consequence,
     where consequence is the station's share of the bottleneck load. PM is
     requested when risk >= `risk_threshold`, and the crew serves the riskiest
     machine first (the same logic as the SUTM maintenance priority score).

Corrective work always has priority over preventive work.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

POLICY_NAMES = {
    "RTF": "Run-to-failure",
    "TBM": "Time-based PM",
    "CBM": "Condition-based",
    "RBM": "Risk-based priority",
}
POLICY_ORDER = ["RTF", "TBM", "CBM", "RBM"]

CORRECTIVE_PRIORITY = -1_000_000.0   # lower value = served first
FIFO_PRIORITY = 0.0


@dataclass(frozen=True)
class Policy:
    kind: str = "CBM"
    pm_interval_h: float = 80.0      # TBM
    threshold: float = 0.4           # CBM (estimated health)
    risk_threshold: float = 0.10     # RBM (risk score)
    inspection_h: float = 8.0        # CBM / RBM: one inspection per shift

    def __post_init__(self):
        if self.kind not in POLICY_NAMES:
            raise ValueError(f"Unknown policy '{self.kind}'. Use one of {list(POLICY_NAMES)}")

    @property
    def name(self) -> str:
        return POLICY_NAMES[self.kind]

    @property
    def uses_inspection(self) -> bool:
        return self.kind in ("CBM", "RBM")

    def with_(self, **kw) -> "Policy":
        return replace(self, **kw)


def pm_priority(policy: Policy, risk: float) -> float:
    """Crew queue priority for a PM request (lower is served first)."""
    return -risk if policy.kind == "RBM" else FIFO_PRIORITY


def consequence_weights(mean_times: dict[str, float], machines: dict[str, int]) -> dict[str, float]:
    """Consequence of losing one machine = its station's load (time per part per
    machine) relative to the most loaded station. The bottleneck gets 1.0."""
    load = {s: mean_times[s] / machines[s] for s in mean_times}
    top = max(load.values())
    return {s: v / top for s, v in load.items()}
