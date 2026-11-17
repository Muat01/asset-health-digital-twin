"""
SimPy model of a serial production line whose failures are driven by asset health.

Line layout (same as production-line-simulation-simpy):
    Cutting -> Machining (2 machines) -> Assembly -> Inspection
finite input buffers, blocking/starving, stochastic processing times and scrap.

What is new here:
* every machine carries a health index H that degrades while it operates
  (see health.py) and its failure rate rises as H falls;
* a shared maintenance crew (SimPy PriorityResource) performs corrective
  repairs and preventive maintenance (PM);
* a maintenance policy (see policies.py) decides when PM is requested and in
  which order the crew serves requests.

Corrective repair is imperfect (restores only part of the lost health);
PM is an overhaul that restores the machine to H = 1.

Time unit: hours. Processing times are given in minutes for readability.
All parameter values are illustrative, not measured from a real plant.
"""
from __future__ import annotations

import random
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import simpy

from health import (HealthParams, corrective_restore, degrade, failure_prob,
                    hazard, inspect)
from policies import (CORRECTIVE_PRIORITY, Policy, consequence_weights,
                      pm_priority)


# ─── Configuration ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class StationConfig:
    name: str
    machines: int
    mean_min: float                 # mean processing time per part (minutes)
    cv: float = 0.25                # CV of processing time
    buffer_size: int = 5            # capacity of the INPUT buffer
    scrap_rate: float = 0.0
    health: HealthParams = field(default_factory=HealthParams)


@dataclass(frozen=True)
class MaintenanceConfig:
    crew_size: int = 1
    mttr_h: float = 3.0             # mean corrective repair time once the crew arrives
    mttr_cv: float = 0.5
    pm_h: float = 1.5               # mean PM (overhaul) duration
    pm_cv: float = 0.2
    cm_restore: float = 0.3         # share of lost health recovered by a corrective repair
    cost_cm: float = 2000.0         # cost per corrective repair (parts, labour, damage)
    cost_pm: float = 600.0          # cost per PM
    cost_line_h: float = 400.0      # cost of running the line per calendar hour


def default_line() -> List[StationConfig]:
    """Baseline line. Machining is the designed bottleneck (2 x 6 min = 3 min/part)."""
    return [
        StationConfig("Cutting", 1, 2.0, buffer_size=5, scrap_rate=0.005,
                      health=HealthParams(life_h=200, mtbf_new_h=400)),
        StationConfig("Machining", 2, 6.0, buffer_size=5, scrap_rate=0.02,
                      health=HealthParams(life_h=120, mtbf_new_h=250)),
        StationConfig("Assembly", 1, 2.6, buffer_size=5, scrap_rate=0.01,
                      health=HealthParams(life_h=160, mtbf_new_h=300)),
        StationConfig("Inspection", 1, 2.2, buffer_size=5, scrap_rate=0.03,
                      health=HealthParams(life_h=300, mtbf_new_h=600)),
    ]


def _seed(*parts) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


# ─── Model ──────────────────────────────────────────────────────────────────
class Part:
    __slots__ = ("t_start",)

    def __init__(self):
        self.t_start: Optional[float] = None


class Machine:
    STATES = ("busy", "blocked", "starved", "down_cm", "down_pm")

    def __init__(self, station: "Station", idx: int, seed: int):
        self.st, self.idx = station, idx
        self.line = station.line
        self.env = station.env
        self.hp = station.cfg.health
        self.label = station.cfg.name if station.cfg.machines == 1 else f"{station.cfg.name} {idx + 1}"
        # independent random streams -> common random numbers across policies
        mk = lambda s: random.Random(_seed(seed, station.cfg.name, idx, s))  # noqa: E731
        self.r_proc, self.r_deg, self.r_fail = mk("proc"), mk("deg"), mk("fail")
        self.r_insp, self.r_rep, self.r_scrap = mk("insp"), mk("rep"), mk("scrap")

        self.h = 1.0
        self.cum = 0.0                          # accumulated hazard
        self.clock = self.r_fail.expovariate(1.0)  # failure when cum >= clock
        self.age = 0.0                          # operating hours since last PM
        self.pm_req = None                      # pending/granted crew request for PM
        self.risk = 0.0
        self.time: Dict[str, float] = {s: 0.0 for s in self.STATES}
        self.n_cm = self.n_pm = self.n_hard = 0

        self.env.process(self._run())
        if self.line.policy.uses_inspection:
            self.env.process(self._inspections())
        if self.line.trace_dt:
            self.env.process(self._trace())

    # -- helpers -------------------------------------------------------------
    def _acc(self, state: str, t0: float) -> None:
        t0 = max(t0, self.line.warmup)
        t1 = self.env.now
        if t1 > t0:
            self.time[state] += t1 - t0

    def _log(self, kind: str, **extra) -> None:
        if self.line.record_events:
            self.line.events.append({"time_h": self.env.now, "machine": self.label,
                                     "station": self.st.cfg.name, "event": kind,
                                     "health": round(self.h, 4), **extra})

    def _counted(self) -> bool:
        return self.env.now >= self.line.warmup

    def _proc_time(self) -> float:
        cv = self.st.cfg.cv
        shape = 1.0 / (cv * cv)
        return self.r_proc.gammavariate(shape, self.st.cfg.mean_min / 60.0 / shape)

    def _repair_time(self, mean: float, cv: float) -> float:
        shape = 1.0 / (cv * cv)
        return self.r_rep.gammavariate(shape, mean / shape)

    def _request_pm(self, priority: float):
        self.pm_req = self.line.crew.request(priority=priority)
        self._log("pm_request", priority=round(priority, 4))

    # -- maintenance actions -------------------------------------------------
    def _do_pm(self):
        """Crew is assigned (pm_req granted): overhaul the machine."""
        m = self.line.mcfg
        t0 = self.env.now
        yield self.env.timeout(self._repair_time(m.pm_h, m.pm_cv))
        self._acc("down_pm", t0)
        self.line.crew.release(self.pm_req)
        self.pm_req = None
        if self._counted():
            self.n_pm += 1
        self.h, self.age = 1.0, 0.0
        self._log("pm_done")

    def _do_corrective(self, hard: bool):
        m = self.line.mcfg
        if self._counted():
            self.n_cm += 1
            self.n_hard += int(hard)
        self._log("failure", hard=hard)
        t0 = self.env.now
        if self.pm_req is not None and self.pm_req.triggered:
            req, self.pm_req = self.pm_req, None     # crew is already here
        else:
            if self.pm_req is not None:
                self.pm_req.cancel()                 # leave the PM queue for now
                self.pm_req = None
            req = self.line.crew.request(priority=CORRECTIVE_PRIORITY)
            yield req
        yield self.env.timeout(self._repair_time(m.mttr_h, m.mttr_cv))
        self._acc("down_cm", t0)
        self.line.crew.release(req)
        self.h = corrective_restore(self.h, m.cm_restore)
        self.cum, self.clock = 0.0, self.r_fail.expovariate(1.0)
        self._log("repair_done")

    def _wants_time_based_pm(self) -> bool:
        p = self.line.policy
        return p.kind == "TBM" and self.pm_req is None and self.age >= p.pm_interval_h

    # -- processes -----------------------------------------------------------
    def _inspections(self):
        p = self.line.policy
        # stagger first inspections so the crew is not flooded at the same instant
        yield self.env.timeout(p.inspection_h * (self.st.index + 0.5 * self.idx + 1) / 6.0)
        while True:
            est = inspect(self.h, self.hp, self.r_insp)
            self.risk = failure_prob(est, p.inspection_h, self.hp) * self.line.consequence[self.st.cfg.name]
            pending = self.pm_req is not None and not self.pm_req.triggered
            if p.kind == "CBM":
                if self.pm_req is None and est < p.threshold:
                    self._request_pm(pm_priority(p, self.risk))
            else:  # RBM
                if self.pm_req is None and self.risk >= p.risk_threshold:
                    self._request_pm(pm_priority(p, self.risk))
                elif pending:                    # refresh queue position with the new risk
                    self.pm_req.cancel()
                    self._request_pm(pm_priority(p, self.risk))
            yield self.env.timeout(p.inspection_h)

    def _trace(self):
        while True:
            self.line.trace.append((self.env.now, self.label, self.h))
            yield self.env.timeout(self.line.trace_dt)

    def _run(self):
        env, cfg = self.env, self.st.cfg
        while True:
            # ---- part boundary: preventive maintenance ----
            if self._wants_time_based_pm():
                self._request_pm(pm_priority(self.line.policy, 0.0))
            if self.pm_req is not None and self.pm_req.triggered:
                yield from self._do_pm()

            # ---- wait for a part (or for the crew, whichever comes first) ----
            t0 = env.now
            get = self.st.inbuf.get()
            if self.pm_req is not None:
                yield get | self.pm_req
                if not get.triggered:
                    get.cancel()
                    self._acc("starved", t0)
                    yield from self._do_pm()
                    continue
            else:
                yield get
            part = get.value
            self._acc("starved", t0)
            if self.st.index == 0:
                part.t_start = env.now
                self.line.wip += 1

            # ---- process with health-driven failures ----
            remaining = self._proc_time()
            while remaining > 1e-12:
                lam = hazard(self.h, self.hp)
                t_fail = (self.clock - self.cum) / lam
                dt = min(remaining, t_fail)
                t0 = env.now
                yield env.timeout(dt)
                self._acc("busy", t0)
                remaining -= dt
                self.age += dt
                self.cum += lam * dt
                self.h = degrade(self.h, dt, self.hp, self.r_deg)
                if t_fail <= dt + 1e-12 or self.h <= 0.0:
                    yield from self._do_corrective(hard=self.h <= 0.0 and t_fail > dt + 1e-12)

            if self._counted():
                self.st.processed += 1

            # ---- quality loss ----
            if self.r_scrap.random() < cfg.scrap_rate:
                self.line.wip -= 1
                if self._counted():
                    self.line.scrapped += 1
                continue

            # ---- pass the part on (blocked while the next buffer is full) ----
            if self.st.outbuf is None:
                self.line.record_exit(part)
            else:
                t0 = env.now
                yield self.st.outbuf.put(part)
                self._acc("blocked", t0)


class Station:
    def __init__(self, line: "Line", cfg: StationConfig, index: int, seed: int):
        self.line, self.cfg, self.index, self.env = line, cfg, index, line.env
        self.inbuf = simpy.Store(self.env, capacity=cfg.buffer_size)
        self.outbuf: Optional[simpy.Store] = None
        self.processed = 0
        self.machines = [Machine(self, i, seed) for i in range(cfg.machines)]


class Line:
    def __init__(self, env: simpy.Environment, configs: List[StationConfig], policy: Policy,
                 mcfg: MaintenanceConfig, warmup: float, seed: int,
                 trace_dt: float = 0.0, record_events: bool = False):
        self.env, self.policy, self.mcfg, self.warmup = env, policy, mcfg, warmup
        self.trace_dt, self.record_events = trace_dt, record_events
        self.crew = simpy.PriorityResource(env, capacity=mcfg.crew_size)
        self.consequence = consequence_weights({c.name: c.mean_min for c in configs},
                                               {c.name: c.machines for c in configs})
        self.wip = self.good = self.scrapped = 0
        self.flow_times: List[float] = []
        self.trace: list = []
        self.events: list = []
        self.stations = [Station(self, c, i, seed) for i, c in enumerate(configs)]
        for a, b in zip(self.stations, self.stations[1:]):
            a.outbuf = b.inbuf
        env.process(self._source())

    def _source(self):
        first = self.stations[0].inbuf
        while True:
            yield first.put(Part())

    def record_exit(self, part: Part) -> None:
        self.wip -= 1
        if self.env.now >= self.warmup:
            self.good += 1
            self.flow_times.append(self.env.now - part.t_start)


# ─── Public API ─────────────────────────────────────────────────────────────
def run(policy: Policy, configs: Optional[List[StationConfig]] = None,
        mcfg: MaintenanceConfig = MaintenanceConfig(), days: float = 60.0,
        warmup_days: float = 7.0, seed: int = 1, trace_dt: float = 0.0,
        record_events: bool = False) -> dict:
    """Run one replication (24/7 operation) and return KPIs.

    trace_dt > 0 records every machine's health every `trace_dt` hours;
    record_events=True keeps a log of failures, PM requests and repairs.
    """
    configs = configs or default_line()
    env = simpy.Environment()
    warmup = warmup_days * 24.0
    horizon = warmup + days * 24.0
    line = Line(env, configs, policy, mcfg, warmup, seed, trace_dt, record_events)
    env.run(until=horizon)

    window = horizon - warmup
    machines = [m for s in line.stations for m in s.machines]
    n_cm = sum(m.n_cm for m in machines)
    n_pm = sum(m.n_pm for m in machines)
    maint_cost = n_cm * mcfg.cost_cm + n_pm * mcfg.cost_pm
    total_cost = maint_cost + mcfg.cost_line_h * window
    out = {
        "policy": policy.kind,
        "seed": seed,
        "throughput_per_h": line.good / window,
        "good_parts": line.good,
        "scrapped_parts": line.scrapped,
        "failures": n_cm,
        "hard_failures": sum(m.n_hard for m in machines),
        "pm_count": n_pm,
        "cm_down_h": sum(m.time["down_cm"] for m in machines),
        "pm_down_h": sum(m.time["down_pm"] for m in machines),
        "maint_cost": maint_cost,
        "total_cost": total_cost,
        "cost_per_part": total_cost / line.good if line.good else float("nan"),
        "maint_cost_per_part": maint_cost / line.good if line.good else float("nan"),
        "avg_flow_time_h": sum(line.flow_times) / len(line.flow_times) if line.flow_times else float("nan"),
        "machines": {},
    }
    for m in machines:
        tot = sum(m.time.values()) or 1.0
        out["machines"][m.label] = {
            "station": m.st.cfg.name,
            **{f"{k}_pct": 100.0 * v / tot for k, v in m.time.items()},
            "availability": 1.0 - (m.time["down_cm"] + m.time["down_pm"]) / tot,
            "failures": m.n_cm, "pm_count": m.n_pm,
        }
    if trace_dt:
        out["trace"] = line.trace
    if record_events:
        out["events"] = line.events
    return out


if __name__ == "__main__":
    import time
    for kind in ("RTF", "TBM", "CBM", "RBM"):
        t = time.time()
        r = run(Policy(kind))
        print(f"{kind}: {r['throughput_per_h']:.2f} parts/h | failures {r['failures']:3d} | PM {r['pm_count']:3d} | "
              f"cost/part {r['cost_per_part']:.2f} | {time.time() - t:.2f}s")
