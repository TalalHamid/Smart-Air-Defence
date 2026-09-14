from dataclasses import dataclass
from typing import Tuple


@dataclass
class ThreatInput:
    threat_type: str  # "ballistic", "drone", "aircraft"
    distance_km: float
    speed_mach: float
    altitude_km: float


def normalize_type(threat_type: str) -> str:
    t = threat_type.strip().lower()
    if "ball" in t:
        return "ballistic"
    if "drone" in t or "uav" in t:
        return "drone"
    if "air" in t or "jet" in t or "fighter" in t:
        return "aircraft"
    return t


def evaluate_threat(threat: ThreatInput) -> Tuple[str, str]:
    """
    Simple Prolog-style rule engine implemented in Python.
    Returns (risk_level, suggested_action).
    """
    t_type = normalize_type(threat.threat_type)
    d = threat.distance_km
    v = threat.speed_mach
    h = threat.altitude_km

    # Base risk from type
    if t_type == "ballistic":
        base_risk = 3
    elif t_type == "aircraft":
        base_risk = 2
    elif t_type == "drone":
        base_risk = 1
    else:
        base_risk = 1

    # Distance contribution
    if d < 80:
        base_risk += 2
    elif d < 200:
        base_risk += 1

    # Speed contribution
    if v > 4.0:
        base_risk += 2
    elif v > 2.0:
        base_risk += 1

    # Altitude contribution (very low or very high is trickier)
    if h < 1.0:
        base_risk += 1
    elif h > 30.0:
        base_risk += 1

    # Map numeric risk to labels
    if base_risk <= 2:
        risk_level = "Low"
    elif base_risk <= 4:
        risk_level = "Medium"
    elif base_risk <= 6:
        risk_level = "High"
    else:
        risk_level = "Critical"

    # Suggested action rules
    if risk_level in ("High", "Critical"):
        if t_type == "ballistic":
            action = "Immediate intercept with long-range ABM battery"
        elif t_type == "aircraft":
            action = "Intercept with medium/long-range SAM and scramble fighters"
        elif t_type == "drone":
            action = "Intercept with short-range drone/SHORAD systems"
        else:
            action = "Intercept with best available systems"
    elif risk_level == "Medium":
        if t_type == "drone":
            action = "Track and be ready for intercept; consider soft-kill/decoy"
        else:
            action = "Track closely and prepare intercept batteries"
    else:  # Low
        action = "Track only; use decoy deployment if behaviour escalates"

    return risk_level, action


