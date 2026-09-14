from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class CSPContext:
    distance_km: float
    speed_mach: float
    altitude_km: float
    threat_type: str


def interceptor_score(interceptor: Dict[str, Any], ctx: CSPContext) -> float:
    """Heuristic score for how suitable an interceptor is."""
    score = 0.0

    # Prefer type match
    if ctx.threat_type == "ballistic" and interceptor["type"] == "long-range":
        score += 5.0
    if ctx.threat_type == "aircraft" and interceptor["type"] in ("medium-range", "long-range"):
        score += 4.0
    if ctx.threat_type == "drone" and interceptor["type"] in ("drone", "short-range"):
        score += 4.0

    # Range closeness (enough range but not hugely overkill)
    range_diff = interceptor["max_range_km"] - ctx.distance_km
    if range_diff >= 0:
        score += 3.0 / (1.0 + range_diff / max(ctx.distance_km, 1.0))

    # Speed advantage
    speed_adv = interceptor["max_speed_mach"] - ctx.speed_mach
    if speed_adv > 0:
        score += 2.0 * speed_adv

    # Radar visibility
    if interceptor["radar_visibility_km"] >= ctx.distance_km:
        score += 1.0

    # Fuel sufficiency (simple model: need distance * factor)
    fuel_need = ctx.distance_km * 0.1
    if interceptor["fuel_units"] >= fuel_need:
        score += 1.0

    return score


def satisfies_constraints(interceptor: Dict[str, Any], ctx: CSPContext) -> bool:
    if interceptor["max_range_km"] < ctx.distance_km:
        return False
    if interceptor["radar_visibility_km"] < ctx.distance_km:
        return False
    if interceptor["inventory"] <= 0:
        return False
    # Simple altitude constraint: assume missiles can reach at least 2x their range in altitude in km
    if ctx.altitude_km > interceptor["max_range_km"] * 0.5:
        return False
    return True


def evaluate_interceptors(
    interceptors: List[Dict[str, Any]], ctx: CSPContext
) -> List[Dict[str, Any]]:
    """
    Return a list of interceptors with feasibility, score, and rationale.
    """
    results = []
    for i in interceptors:
        reasons = []
        feasible = True
        if i["max_range_km"] < ctx.distance_km:
            feasible = False
            reasons.append("Insufficient range")
        if i["radar_visibility_km"] < ctx.distance_km:
            feasible = False
            reasons.append("Radar cannot track at distance")
        if i["inventory"] <= 0:
            feasible = False
            reasons.append("No inventory")
        if ctx.altitude_km > i["max_range_km"] * 0.5:
            feasible = False
            reasons.append("Altitude too high for this missile")

        score = interceptor_score(i, ctx) if feasible else 0.0
        if feasible:
            # Add short rationale for score drivers
            if ctx.threat_type == "ballistic" and i["type"] == "long-range":
                reasons.append("Type match for ballistic")
            if ctx.threat_type == "aircraft" and i["type"] in ("medium-range", "long-range"):
                reasons.append("Type match for aircraft")
            if ctx.threat_type == "drone" and i["type"] in ("drone", "short-range"):
                reasons.append("Type match for drone")
            if i["max_range_km"] >= ctx.distance_km:
                reasons.append("Range covers target")
            if i["max_speed_mach"] > ctx.speed_mach:
                reasons.append("Speed advantage")
            if i["fuel_units"] >= ctx.distance_km * 0.1:
                reasons.append("Fuel sufficient")
            if i["radar_visibility_km"] >= ctx.distance_km:
                reasons.append("Radar coverage OK")

        results.append(
            {
                "interceptor": i,
                "feasible": feasible,
                "score": round(score, 2),
                "reasons": reasons,
            }
        )

    # Sort by score descending, feasible first
    results.sort(key=lambda r: (r["feasible"], r["score"]), reverse=True)
    return results


def choose_interceptors(
    interceptors: List[Dict[str, Any]], ctx: CSPContext, max_to_use: int = 2
) -> List[Dict[str, Any]]:
    """
    Simple CSP solver:
    - Filter by hard constraints.
    - Sort by heuristic score.
    - Pick top-k as solution.
    """
    evaluated = evaluate_interceptors(interceptors, ctx)
    feasible = [r["interceptor"] for r in evaluated if r["feasible"]]
    return feasible[:max_to_use]


