import math
import random
from dataclasses import dataclass
from typing import Tuple, Dict


@dataclass
class GAContext:
    distance_km: float
    threat_speed_km_s: float
    interceptor_speed_km_s: float


def simulate_interception(
    angle_deg: float, launch_delay_s: float, ctx: GAContext, max_time_s: float = 600.0
) -> Tuple[float, float, float]:
    """
    Very simplified 2D interception model.
    - Threat starts at (distance, 0) moving towards origin at constant speed.
    - Interceptor starts at origin, launched after launch_delay, with fixed speed and angle.
    Returns (miss_distance_km, collision_time_s, energy_cost).
    """
    angle_rad = math.radians(angle_deg)

    # Brute force simulate with small time steps
    dt = 0.5
    t = 0.0
    min_dist = float("inf")
    best_t = max_time_s

    while t <= max_time_s:
        # Threat position
        tx = ctx.distance_km - ctx.threat_speed_km_s * t
        ty = 0.0

        # Interceptor position (only after launch_delay)
        if t < launch_delay_s:
            ix, iy = 0.0, 0.0
        else:
            tau = t - launch_delay_s
            ix = ctx.interceptor_speed_km_s * tau * math.cos(angle_rad)
            iy = ctx.interceptor_speed_km_s * tau * math.sin(angle_rad)

        dx = tx - ix
        dy = ty - iy
        dist = math.hypot(dx, dy)

        if dist < min_dist:
            min_dist = dist
            best_t = t

        t += dt

    # Energy model: proportional to flight time of interceptor
    flight_time = max(0.0, best_t - launch_delay_s)
    energy = flight_time * (ctx.interceptor_speed_km_s ** 2)
    return min_dist, best_t, energy


def fitness(angle_deg: float, launch_delay_s: float, ctx: GAContext) -> float:
    miss_dist, t_hit, energy = simulate_interception(angle_deg, launch_delay_s, ctx)
    # We want to minimize miss distance, time, and energy.
    # Combine them into a single scalar; smaller is better.
    return miss_dist * 100.0 + t_hit * 0.5 + energy * 0.05


def run_ga(ctx: GAContext, generations: int = 40, population_size: int = 40) -> Dict:
    """
    Basic continuous GA optimizing (angle_deg, launch_delay_s).
    Angle in [5, 85] degrees, launch delay in [0, 60] seconds.
    """
    angle_bounds = (5.0, 85.0)
    delay_bounds = (0.0, 60.0)

    def random_individual():
        return [
            random.uniform(*angle_bounds),
            random.uniform(*delay_bounds),
        ]

    def mutate(ind, rate=0.2, sigma_angle=5.0, sigma_delay=3.0):
        if random.random() < rate:
            ind[0] += random.gauss(0, sigma_angle)
        if random.random() < rate:
            ind[1] += random.gauss(0, sigma_delay)
        # Clip to bounds
        ind[0] = max(angle_bounds[0], min(angle_bounds[1], ind[0]))
        ind[1] = max(delay_bounds[0], min(delay_bounds[1], ind[1]))

    def crossover(a, b):
        alpha = random.random()
        child1 = [alpha * a[0] + (1 - alpha) * b[0], alpha * a[1] + (1 - alpha) * b[1]]
        alpha = random.random()
        child2 = [alpha * b[0] + (1 - alpha) * a[0], alpha * b[1] + (1 - alpha) * a[1]]
        return child1, child2

    # Initialize population
    population = [random_individual() for _ in range(population_size)]

    for _ in range(generations):
        # Evaluate fitness
        scored = [
            (fitness(ind[0], ind[1], ctx), ind) for ind in population
        ]
        scored.sort(key=lambda x: x[0])  # lower is better

        # Elitism: keep top 20%
        elite_count = max(2, population_size // 5)
        new_pop = [ind for _, ind in scored[:elite_count]]

        # Tournament selection + crossover
        while len(new_pop) < population_size:
            a = min(random.sample(scored, 2), key=lambda x: x[0])[1]
            b = min(random.sample(scored, 2), key=lambda x: x[0])[1]
            child1, child2 = crossover(a, b)
            mutate(child1)
            mutate(child2)
            new_pop.append(child1)
            if len(new_pop) < population_size:
                new_pop.append(child2)

        population = new_pop

    # Final best individual
    final_scored = [(fitness(ind[0], ind[1], ctx), ind) for ind in population]
    best_fit, best_ind = min(final_scored, key=lambda x: x[0])
    miss_dist, t_hit, energy = simulate_interception(best_ind[0], best_ind[1], ctx)

    return {
        "angle_deg": best_ind[0],
        "launch_delay_s": best_ind[1],
        "estimated_collision_time_s": t_hit,
        "estimated_miss_distance_km": miss_dist,
        "energy_cost": energy,
        "fitness": best_fit,
    }


