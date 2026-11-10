"""
Asset health model: degradation, health-dependent hazard and noisy inspections.

Health index H is in [0, 1]: 1 = as good as new, 0 = functional failure.

* Degradation: a stationary gamma process driven by OPERATING time. Over its
  life the machine loses health at an average rate of 1 / life_h per operating
  hour; `cv` is the coefficient of variation of the total life.
* Hazard: proportional-hazards form (Cox / Jardine-style PHM) with degradation
  as the covariate:  lambda(H) = lambda0 * exp(gamma * (1 - H)).
  A healthy machine still fails occasionally (random failures); a worn one
  fails far more often. Reaching H = 0 is a certain (hard) failure.
* Inspection: non-intrusive condition check (like a visual or thermal score)
  that returns the true H plus Gaussian noise.

Time unit: hours. All parameter values in this project are illustrative.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthParams:
    life_h: float = 120.0        # mean operating hours for H to fall from 1 to 0
    cv: float = 0.3              # variability of the degradation path
    mtbf_new_h: float = 250.0    # mean operating time between failures when H = 1
    gamma: float = 3.0           # sensitivity of the hazard to degradation
    insp_sigma: float = 0.05     # standard deviation of the inspection error

    @property
    def lambda0(self) -> float:
        return 1.0 / self.mtbf_new_h


def degrade(h: float, dt: float, p: HealthParams, rng: random.Random) -> float:
    """Return health after `dt` operating hours (gamma-process increment)."""
    if dt <= 0:
        return h
    shape = dt / (p.life_h * p.cv * p.cv)
    loss = rng.gammavariate(shape, p.cv * p.cv) if shape > 0 else 0.0
    return max(0.0, h - loss)


def hazard(h: float, p: HealthParams) -> float:
    """Failure rate (per operating hour) at health h."""
    return p.lambda0 * math.exp(p.gamma * (1.0 - h))


def failure_prob(h: float, horizon_h: float, p: HealthParams) -> float:
    """Approximate probability of failing within the next `horizon_h` operating
    hours, assuming health stays near h and degrades at its mean rate."""
    if horizon_h <= 0:
        return 0.0
    h_end = max(0.0, h - horizon_h / p.life_h)
    if h_end <= 0.0:
        return 1.0
    # trapezoid on the hazard along the mean path
    cum = 0.5 * (hazard(h, p) + hazard(h_end, p)) * horizon_h
    return 1.0 - math.exp(-cum)


def inspect(h: float, p: HealthParams, rng: random.Random) -> float:
    """Noisy estimate of the health index, clipped to [0, 1]."""
    return min(1.0, max(0.0, h + rng.gauss(0.0, p.insp_sigma)))


def corrective_restore(h: float, fraction: float) -> float:
    """Imperfect repair: recover `fraction` of the lost health."""
    return h + fraction * (1.0 - h)
