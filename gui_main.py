import sys
import math
from datetime import datetime
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from db import init_db, fetch_interceptors, log_engagement, list_engagements
from expert_system import ThreatInput, evaluate_threat, normalize_type
from csp_engine import CSPContext, choose_interceptors, evaluate_interceptors
from ga_trajectory import GAContext, run_ga


class TrajectoryCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure(figsize=(7, 4), tight_layout=True)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self.setMinimumHeight(320)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._step_animation)
        self.t_vals = []
        self.tx = []
        self.ty = []
        self.ix = []
        self.iy = []
        self.idx = 0
        self.threat_marker = None
        self.interceptor_marker = None

    def plot_trajectory(self, ctx: GAContext, ga_result: dict):
        self.ax.clear()
        angle_deg = ga_result["angle_deg"]
        angle_rad = angle_deg * 3.14159 / 180.0

        # Simple straight-line interceptor trajectory and straight-line threat
        self.t_vals = [i for i in range(0, int(ga_result["estimated_collision_time_s"]) + 1, 1)]
        self.tx = [ctx.distance_km - ctx.threat_speed_km_s * t for t in self.t_vals]
        self.ty = [0.0 for _ in self.t_vals]

        self.ix = [ctx.interceptor_speed_km_s * max(0, t - ga_result["launch_delay_s"]) * math.cos(
            angle_rad
        ) for t in self.t_vals]
        self.iy = [ctx.interceptor_speed_km_s * max(0, t - ga_result["launch_delay_s"]) * math.sin(
            angle_rad
        ) for t in self.t_vals]

        # Collision marker (estimated)
        t_hit = ga_result["estimated_collision_time_s"]
        tx_hit = ctx.distance_km - ctx.threat_speed_km_s * t_hit
        tau = max(0, t_hit - ga_result["launch_delay_s"])
        ix_hit = ctx.interceptor_speed_km_s * tau * math.cos(angle_rad)
        iy_hit = ctx.interceptor_speed_km_s * tau * math.sin(angle_rad)

        self.ax.plot(self.tx, self.ty, label="Threat path", color="red")
        self.ax.plot(self.ix, self.iy, label="Interceptor path", color="blue")
        self.ax.scatter([tx_hit], [iy_hit], color="green", marker="*", s=120, label="Intercept")
        # Live markers
        self.threat_marker = self.ax.scatter([self.tx[0]], [self.ty[0]], color="red", s=60)
        self.interceptor_marker = self.ax.scatter([self.ix[0]], [self.iy[0]], color="blue", s=60)
        # Fix axis limits to avoid jitter
        x_vals = self.tx + self.ix
        y_vals = self.ty + self.iy
        x_min, x_max = min(x_vals), max(x_vals)
        y_min, y_max = min(y_vals), max(y_vals)
        pad_x = max(5.0, abs(x_max - x_min) * 0.1)
        pad_y = max(2.0, abs(y_max - y_min) * 0.1 + 1.0)
        self.ax.set_xlim(x_min - pad_x, x_max + pad_x)
        self.ax.set_ylim(y_min - pad_y, y_max + pad_y)
        self.ax.set_xlabel("X position (km)")
        self.ax.set_ylabel("Y position (km)")
        self.ax.set_title("Approximate Interception Trajectory")
        self.ax.legend()
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.draw()
        self.idx = 0
        self.timer.start(180)  # smoother animation

    def _step_animation(self):
        if not self.t_vals:
            return
        self.idx += 1
        if self.idx >= len(self.t_vals):
            self.timer.stop()
            return
        self.threat_marker.set_offsets([[self.tx[self.idx], self.ty[self.idx]]])
        self.interceptor_marker.set_offsets([[self.ix[self.idx], self.iy[self.idx]]])
        self.draw_idle()

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Anti-Missile Defence & Threat Assessment System")
        self.resize(1100, 700)

        self._build_ui()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        title = QtWidgets.QLabel(
            "<h2 style='color:#2c3e50;'>Smart Anti-Missile Defence & Threat Assessment System</h2>"
        )
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs, 1)

        # Threat analysis tab
        self.tab_threat = QtWidgets.QWidget()
        tabs.addTab(self.tab_threat, "Threat Analysis")

        # Engagement history tab
        self.tab_history = QtWidgets.QWidget()
        tabs.addTab(self.tab_history, "Engagement Logs")

        self._build_threat_tab()
        self._build_history_tab()

        # Add scroll area around main content
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(central)
        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.addWidget(scroll)
        self.setCentralWidget(container)

    def _build_threat_tab(self):
        layout = QtWidgets.QGridLayout(self.tab_threat)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)

        # Left panel: threat input
        left = QtWidgets.QGroupBox("Threat Scenario Input")
        left_layout = QtWidgets.QFormLayout(left)

        self.cmb_type = QtWidgets.QComboBox()
        self.cmb_type.addItems(["Ballistic missile", "Drone", "Aircraft"])

        self.spin_distance = QtWidgets.QDoubleSpinBox()
        self.spin_distance.setRange(10, 2000)
        self.spin_distance.setValue(350)
        self.spin_distance.setSuffix(" km")

        self.spin_speed = QtWidgets.QDoubleSpinBox()
        self.spin_speed.setRange(0.1, 10.0)
        self.spin_speed.setValue(3.5)
        self.spin_speed.setSingleStep(0.1)
        self.spin_speed.setSuffix(" Mach")

        self.spin_altitude = QtWidgets.QDoubleSpinBox()
        self.spin_altitude.setRange(0.1, 80.0)
        self.spin_altitude.setValue(25.0)
        self.spin_altitude.setSingleStep(0.5)
        self.spin_altitude.setSuffix(" km")

        self.btn_run = QtWidgets.QPushButton("Run Full Assessment")
        self.btn_run.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.btn_run.clicked.connect(self.on_run_assessment)

        left_layout.addRow("Threat type:", self.cmb_type)
        left_layout.addRow("Distance:", self.spin_distance)
        left_layout.addRow("Speed:", self.spin_speed)
        left_layout.addRow("Altitude:", self.spin_altitude)
        left_layout.addRow(self.btn_run)

        layout.addWidget(left, 0, 0)

        # Right panel: results + trajectory
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)

        result_group = QtWidgets.QGroupBox("Assessment Result")
        result_layout = QtWidgets.QGridLayout(result_group)

        self.lbl_risk = QtWidgets.QLabel("-")
        self.lbl_risk.setStyleSheet("font-weight:bold; color:#c0392b;")
        self.lbl_action = QtWidgets.QLabel("-")
        self.lbl_interceptors = QtWidgets.QLabel("-")

        result_layout.addWidget(QtWidgets.QLabel("Risk level:"), 0, 0)
        result_layout.addWidget(self.lbl_risk, 0, 1)
        result_layout.addWidget(QtWidgets.QLabel("Suggested action:"), 1, 0)
        result_layout.addWidget(self.lbl_action, 1, 1)
        result_layout.addWidget(QtWidgets.QLabel("Selected interceptors:"), 2, 0)
        result_layout.addWidget(self.lbl_interceptors, 2, 1)

        rationale_group = QtWidgets.QGroupBox("Interceptor Selection Rationale")
        rationale_layout = QtWidgets.QVBoxLayout(rationale_group)
        self.tbl_csp = QtWidgets.QTableWidget()
        self.tbl_csp.setColumnCount(4)
        self.tbl_csp.setHorizontalHeaderLabels(["Interceptor", "Feasible", "Score", "Reasons"])
        self.tbl_csp.horizontalHeader().setStretchLastSection(True)
        self.tbl_csp.setMinimumHeight(160)
        rationale_layout.addWidget(self.tbl_csp)

        ga_group = QtWidgets.QGroupBox("Genetic Algorithm – Optimal Interception")
        ga_layout = QtWidgets.QGridLayout(ga_group)

        self.lbl_angle = QtWidgets.QLabel("-")
        self.lbl_delay = QtWidgets.QLabel("-")
        self.lbl_collision_time = QtWidgets.QLabel("-")
        self.lbl_miss_distance = QtWidgets.QLabel("-")

        ga_layout.addWidget(QtWidgets.QLabel("Launch angle:"), 0, 0)
        ga_layout.addWidget(self.lbl_angle, 0, 1)
        ga_layout.addWidget(QtWidgets.QLabel("Launch delay:"), 1, 0)
        ga_layout.addWidget(self.lbl_delay, 1, 1)
        ga_layout.addWidget(QtWidgets.QLabel("Estimated collision time:"), 2, 0)
        ga_layout.addWidget(self.lbl_collision_time, 2, 1)
        ga_layout.addWidget(QtWidgets.QLabel("Estimated miss distance:"), 3, 0)
        ga_layout.addWidget(self.lbl_miss_distance, 3, 1)

        self.canvas = TrajectoryCanvas()

        right_layout.addWidget(result_group)
        right_layout.addWidget(rationale_group)
        right_layout.addWidget(ga_group)
        right_layout.addWidget(self.canvas, 1)

        layout.addWidget(right, 0, 1)

    def _build_history_tab(self):
        layout = QtWidgets.QVBoxLayout(self.tab_history)
        self.table_history = QtWidgets.QTableWidget()
        self.table_history.setColumnCount(8)
        self.table_history.setHorizontalHeaderLabels(
            [
                "Time",
                "Threat",
                "Distance (km)",
                "Speed (Mach)",
                "Altitude (km)",
                "Risk",
                "Action",
                "Interceptors",
            ]
        )
        self.table_history.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_history)

        btn_refresh = QtWidgets.QPushButton("Refresh Logs")
        btn_refresh.clicked.connect(self.load_history)
        layout.addWidget(btn_refresh, alignment=QtCore.Qt.AlignRight)

        self.load_history()

    def load_history(self):
        rows = list_engagements(limit=100)
        self.table_history.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.table_history.setItem(r, 0, QtWidgets.QTableWidgetItem(row[1]))
            self.table_history.setItem(r, 1, QtWidgets.QTableWidgetItem(row[2]))
            self.table_history.setItem(r, 2, QtWidgets.QTableWidgetItem(f"{row[3]:.1f}"))
            self.table_history.setItem(r, 3, QtWidgets.QTableWidgetItem(f"{row[4]:.2f}"))
            self.table_history.setItem(r, 4, QtWidgets.QTableWidgetItem(f"{row[5]:.1f}"))
            self.table_history.setItem(r, 5, QtWidgets.QTableWidgetItem(row[6]))
            self.table_history.setItem(r, 6, QtWidgets.QTableWidgetItem(row[7]))
            self.table_history.setItem(r, 7, QtWidgets.QTableWidgetItem(row[8] or ""))

    def on_run_assessment(self):
        threat_label = self.cmb_type.currentText()
        threat_type = normalize_type(threat_label)
        distance = self.spin_distance.value()
        speed_mach = self.spin_speed.value()
        altitude = self.spin_altitude.value()

        threat = ThreatInput(threat_type=threat_type, distance_km=distance,
                             speed_mach=speed_mach, altitude_km=altitude)
        risk, action = evaluate_threat(threat)

        self.lbl_risk.setText(risk)
        self.lbl_action.setText(action)

        # CSP: choose interceptors
        all_int = fetch_interceptors()
        ctx = CSPContext(
            distance_km=distance,
            speed_mach=speed_mach,
            altitude_km=altitude,
            threat_type=threat_type,
        )
        evaluated = evaluate_interceptors(all_int, ctx)
        self._populate_csp_table(evaluated)
        chosen = [r["interceptor"] for r in evaluated if r["feasible"]][:2]
        if chosen:
            names = ", ".join(i["name"] for i in chosen)
        else:
            names = "No feasible interceptors (constraints too strict)"
        self.lbl_interceptors.setText(names)

        # GA: assume interceptor speed based on first chosen or default
        if chosen:
            interceptor_speed_mach = chosen[0]["max_speed_mach"]
        else:
            interceptor_speed_mach = max(2.0, speed_mach + 0.5)

        # Convert Mach to km/s (very rough: Mach 1 ≈ 0.34 km/s at altitude)
        threat_speed_km_s = speed_mach * 0.34
        interceptor_speed_km_s = interceptor_speed_mach * 0.34
        ga_ctx = GAContext(
            distance_km=distance,
            threat_speed_km_s=threat_speed_km_s,
            interceptor_speed_km_s=interceptor_speed_km_s,
        )

        ga_result = run_ga(ga_ctx)

        self.lbl_angle.setText(f"{ga_result['angle_deg']:.1f} °")
        self.lbl_delay.setText(f"{ga_result['launch_delay_s']:.1f} s")
        self.lbl_collision_time.setText(f"{ga_result['estimated_collision_time_s']:.1f} s")
        self.lbl_miss_distance.setText(f"{ga_result['estimated_miss_distance_km']*1000:.1f} m")

        # Plot trajectory
        self.canvas.plot_trajectory(ga_ctx, ga_result)

        # Log engagement
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        log_engagement(
            timestamp=ts,
            threat_type=threat_label,
            distance_km=distance,
            speed_mach=speed_mach,
            altitude_km=altitude,
            risk_level=risk,
            suggested_action=action,
            chosen_interceptors=names,
            ga_result=str(ga_result),
        )
        self.load_history()

    def _populate_csp_table(self, evaluated):
        self.tbl_csp.setRowCount(len(evaluated))
        for r, row in enumerate(evaluated):
            self.tbl_csp.setItem(r, 0, QtWidgets.QTableWidgetItem(row["interceptor"]["name"]))
            feasible_text = "Yes" if row["feasible"] else "No"
            self.tbl_csp.setItem(r, 1, QtWidgets.QTableWidgetItem(feasible_text))
            self.tbl_csp.setItem(r, 2, QtWidgets.QTableWidgetItem(f"{row['score']:.2f}"))
            reasons = "; ".join(row["reasons"]) if row["reasons"] else "-"
            self.tbl_csp.setItem(r, 3, QtWidgets.QTableWidgetItem(reasons))


def run_app():
    init_db()
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_app()


