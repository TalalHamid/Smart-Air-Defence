## Smart Anti-Missile Defence and Threat Assessment System

This project is a **Smart Anti-Missile Defence and Threat Assessment System** that combines:

- **Expert System (Prolog-style rules in Python)** for threat classification and action recommendation
- **CSP (Constraint Satisfaction Problem)** for selecting the best interceptor missiles
- **GA (Genetic Algorithm)** for computing an optimal interception trajectory
- **SQLite database** for interceptor inventory and engagement logs
- **PyQt5 GUI** for an interactive and visually appealing interface

### 1. Features

- **Threat Assessment**
  - Identifies threat type: ballistic missile, drone, aircraft
  - Evaluates risk level (Low, Medium, High, Critical)
  - Suggests action: intercept, track, decoy deployment

- **CSP Interceptor Selection**
  - Chooses best interceptor missiles under constraints:
    - Missile range
    - Speed
    - Fuel
    - Launch angle
    - Radar visibility

- **GA Trajectory Optimization**
  - Computes interception parameters to achieve:
    - Minimum collision time
    - Maximum accuracy (minimal miss distance)
    - Lower energy usage

- **Database**
  - `interceptors` table with capabilities and inventory
  - `engagement_logs` table for every simulated engagement

### 2. Installation

1. Create and activate a virtual environment (recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Running the Application

From the project root:

```bash
python main.py
```

### 4. High-Level Architecture

- `main.py` – entry point, starts the PyQt5 GUI
- `gui_main.py` – main GUI windows and layout
- `db.py` – SQLite database initialization and utility functions
- `expert_system.py` – rule-based threat assessment module
- `csp_engine.py` – interceptor selection under constraints
- `ga_trajectory.py` – genetic algorithm for interception trajectory

### 5. Notes

- The system is **simulation-oriented** and meant for academic/educational use, not for real military deployment.
- You can extend the rules, interceptor database, and optimization settings to make the scenarios richer.


