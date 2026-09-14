import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Tuple


DB_PATH = Path("defence.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist and seed some interceptor data."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interceptors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            max_range_km REAL NOT NULL,
            max_speed_mach REAL NOT NULL,
            fuel_units REAL NOT NULL,
            min_launch_angle REAL NOT NULL,
            max_launch_angle REAL NOT NULL,
            radar_visibility_km REAL NOT NULL,
            inventory INTEGER NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS engagement_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            threat_type TEXT NOT NULL,
            distance_km REAL NOT NULL,
            speed_mach REAL NOT NULL,
            altitude_km REAL NOT NULL,
            risk_level TEXT NOT NULL,
            suggested_action TEXT NOT NULL,
            chosen_interceptors TEXT,
            ga_result TEXT
        )
        """
    )

    # Seed sample interceptors if table is empty
    cur.execute("SELECT COUNT(*) FROM interceptors")
    count = cur.fetchone()[0]
    if count == 0:
        sample_data = [
            (
                "Aegis-1",
                "long-range",
                600.0,
                4.0,
                100.0,
                20.0,
                75.0,
                800.0,
                12,
            ),
            (
                "Aegis-2",
                "medium-range",
                250.0,
                3.0,
                70.0,
                15.0,
                70.0,
                500.0,
                20,
            ),
            (
                "SkyShield",
                "short-range",
                80.0,
                2.5,
                40.0,
                10.0,
                60.0,
                200.0,
                30,
            ),
            (
                "DroneHunter",
                "drone",
                40.0,
                1.5,
                25.0,
                5.0,
                55.0,
                120.0,
                25,
            ),
        ]
        cur.executemany(
            """
            INSERT INTO interceptors (
                name, type, max_range_km, max_speed_mach, fuel_units,
                min_launch_angle, max_launch_angle, radar_visibility_km, inventory
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            sample_data,
        )

    conn.commit()
    conn.close()


def fetch_interceptors() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM interceptors WHERE inventory > 0")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def log_engagement(
    timestamp: str,
    threat_type: str,
    distance_km: float,
    speed_mach: float,
    altitude_km: float,
    risk_level: str,
    suggested_action: str,
    chosen_interceptors: str,
    ga_result: str,
) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO engagement_logs (
            timestamp, threat_type, distance_km, speed_mach, altitude_km,
            risk_level, suggested_action, chosen_interceptors, ga_result
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            threat_type,
            distance_km,
            speed_mach,
            altitude_km,
            risk_level,
            suggested_action,
            chosen_interceptors,
            ga_result,
        ),
    )
    conn.commit()
    conn.close()


def list_engagements(limit: int = 50) -> List[Tuple]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, timestamp, threat_type, distance_km, speed_mach, altitude_km,
               risk_level, suggested_action, chosen_interceptors
        FROM engagement_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


