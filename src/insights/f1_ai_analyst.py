"""
f1_ai_analyst.py
-----------------
AI-powered race analyst that reads live telemetry and generates
natural language commentary using a Hugging Face model.
"""

import os
import time
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QComboBox
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt, QThread, Signal
from src.gui.pit_wall_window import PitWallWindow

# Load environment variables from .env file
load_dotenv()

# How many seconds between AI commentary updates
COMMENTARY_INTERVAL = 15

# The Hugging Face model we are using
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"


class AICommentaryWorker(QThread):
    """
    Runs the Hugging Face API call in a background thread
    so the UI never freezes while waiting for a response.
    """
    commentary_ready = Signal(str)   # emitted when AI response arrives
    error_occurred   = Signal(str)   # emitted if something goes wrong

    def __init__(self, client: InferenceClient, prompt: str):
        super().__init__()
        self.client = client
        self.prompt = prompt

    def run(self):
        """Called automatically when the thread starts."""
        try:
            response = self.client.text_generation(
                self.prompt,
                max_new_tokens=180,
                temperature=0.7,
                repetition_penalty=1.1,
                stop_sequences=["</s>", "[INST]"],
            )
            # Clean up the response
            text = response.strip()
            self.commentary_ready.emit(text)
        except Exception as e:
            self.error_occurred.emit(f"AI Error: {str(e)}")


class F1AIAnalystWindow(PitWallWindow):
    """
    A PitWallWindow that shows AI-generated race commentary
    based on live telemetry data from the replay.
    """

    def __init__(self):
        # Track the last time we asked for commentary
        self._last_commentary_time = 0.0
        self._current_frame_data   = None
        self._worker               = None
        self._commentary_history   = []   # list of strings
        self._selected_driver      = None

        # Set up the Hugging Face client
        token = os.getenv("HF_API_TOKEN")
        if not token:
            raise EnvironmentError(
                "HF_API_TOKEN not found in .env file. "
                "Please add it and restart."
            )
        self.client = InferenceClient(token=token)

        # Call parent __init__ AFTER setting instance variables
        # because PitWallWindow.__init__ calls setup_ui() immediately
        super().__init__()
        self.setWindowTitle("F1 AI Race Analyst")
        self.resize(520, 700)

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def setup_ui(self):
        """Build the window layout."""
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Header ──────────────────────────────────────────────────
        header = QLabel("🏎️  F1 AI Race Analyst")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        root.addWidget(header)

        subtitle = QLabel("Powered by Mistral-7B via Hugging Face")
        subtitle.setFont(QFont("Arial", 10))
        subtitle.setStyleSheet("color: gray;")
        root.addWidget(subtitle)

        # ── Driver selector ─────────────────────────────────────────
        driver_row = QHBoxLayout()
        driver_label = QLabel("Focus on driver:")
        driver_label.setFont(QFont("Arial", 11))
        self.driver_combo = QComboBox()
        self.driver_combo.addItem("All drivers (overview)")
        self.driver_combo.setFont(QFont("Arial", 11))
        self.driver_combo.currentTextChanged.connect(self._on_driver_changed)
        driver_row.addWidget(driver_label)
        driver_row.addWidget(self.driver_combo)
        root.addLayout(driver_row)

        # ── Live telemetry snapshot ──────────────────────────────────
        snapshot_label = QLabel("Live Telemetry Snapshot:")
        snapshot_label.setFont(QFont("Arial", 11, QFont.Bold))
        root.addWidget(snapshot_label)

        self.snapshot_box = QTextEdit()
        self.snapshot_box.setReadOnly(True)
        self.snapshot_box.setFont(QFont("Courier", 9))
        self.snapshot_box.setMaximumHeight(140)
        self.snapshot_box.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; border-radius: 4px;"
        )
        root.addWidget(self.snapshot_box)

        # ── AI Commentary ────────────────────────────────────────────
        commentary_label = QLabel("AI Commentary:")
        commentary_label.setFont(QFont("Arial", 11, QFont.Bold))
        root.addWidget(commentary_label)

        self.commentary_box = QTextEdit()
        self.commentary_box.setReadOnly(True)
        self.commentary_box.setFont(QFont("Arial", 11))
        self.commentary_box.setStyleSheet(
            "background-color: #0d0d0d; color: #f0f0f0; "
            "border-radius: 4px; padding: 6px;"
        )
        root.addWidget(self.commentary_box, stretch=1)

        # ── Controls ─────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self.ask_btn = QPushButton("Ask AI Now")
        self.ask_btn.setFixedHeight(34)
        self.ask_btn.clicked.connect(self._trigger_commentary)
        btn_row.addWidget(self.ask_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedHeight(34)
        self.clear_btn.setFixedWidth(70)
        self.clear_btn.clicked.connect(self._clear_commentary)
        btn_row.addWidget(self.clear_btn)

        root.addLayout(btn_row)

        # ── Status label ─────────────────────────────────────────────
        self.status_label = QLabel("Waiting for telemetry stream...")
        self.status_label.setFont(QFont("Arial", 9))
        self.status_label.setStyleSheet("color: gray;")
        root.addWidget(self.status_label)

    # ------------------------------------------------------------------
    # Telemetry callbacks  (called by PitWallWindow base class)
    # ------------------------------------------------------------------

    def on_telemetry_data(self, data: dict):
        """Receives live telemetry every frame from the replay."""
        self._current_frame_data = data
        self._update_driver_list(data)
        self._update_snapshot(data)

        # Auto-trigger commentary every COMMENTARY_INTERVAL seconds
        now = time.time()
        if now - self._last_commentary_time >= COMMENTARY_INTERVAL:
            self._trigger_commentary()

    def on_connection_status_changed(self, status: str):
        self.status_label.setText(f"Stream: {status}")
        if status == "Connected":
            self.status_label.setStyleSheet("color: green;")
        elif status == "Connecting...":
            self.status_label.setStyleSheet("color: orange;")
        else:
            self.status_label.setStyleSheet("color: red;")

    def on_stream_error(self, error_msg: str):
        self._append_commentary(f"⚠️ Stream error: {error_msg}", color="#ff6b6b")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_driver_changed(self, text: str):
        self._selected_driver = None if text == "All drivers (overview)" else text

    def _update_driver_list(self, data: dict):
        """Add any new drivers to the combo box."""
        frame = data.get("frame")
        if not frame:
            return
        drivers = frame.get("drivers", {})
        current_items = [
            self.driver_combo.itemText(i)
            for i in range(self.driver_combo.count())
        ]
        for code in sorted(drivers.keys()):
            if code not in current_items:
                self.driver_combo.addItem(code)

    def _update_snapshot(self, data: dict):
        """Update the raw telemetry snapshot box."""
        frame = data.get("frame")
        if not frame:
            return

        drivers  = frame.get("drivers", {})
        lap      = data.get("session_data", {}).get("lap", "?")
        status   = data.get("track_status", "GREEN")
        speed    = data.get("playback_speed", 1.0)
        paused   = data.get("is_paused", False)

        lines = [
            f"Lap: {lap}  |  Track: {status}  |  "
            f"Speed: {speed}x  |  {'PAUSED' if paused else 'LIVE'}",
            "",
        ]

        # Show top 5 drivers by position
        sorted_drivers = sorted(
            drivers.items(),
            key=lambda kv: kv[1].get("position", 99)
        )[:5]

        for code, info in sorted_drivers:
            pos   = info.get("position", "?")
            spd   = info.get("speed", 0)
            gear  = info.get("gear", "?")
            drs   = "DRS" if int(info.get("drs", 0)) >= 10 else "   "
            lap_n = info.get("lap", "?")
            lines.append(
                f"P{pos:>2} {code}  "
                f"Lap {lap_n}  {spd:>3.0f}km/h  G{gear}  {drs}"
            )

        self.snapshot_box.setText("\n".join(lines))

    def _build_prompt(self, data: dict) -> str:
        """
        Convert the current telemetry snapshot into a prompt
        the AI model can understand and respond to.
        """
        frame   = data.get("frame", {})
        drivers = frame.get("drivers", {}) if frame else {}
        lap     = data.get("session_data", {}).get("lap", "?")
        leader  = data.get("session_data", {}).get("leader", "?")
        status  = data.get("track_status", "GREEN")
        total   = data.get("session_data", {}).get("total_laps", "?")

        # Build driver summary
        sorted_drivers = sorted(
            drivers.items(),
            key=lambda kv: kv[1].get("position", 99)
        )

        driver_lines = []
        for code, info in sorted_drivers[:10]:
            pos   = info.get("position", "?")
            spd   = info.get("speed", 0)
            gear  = info.get("gear", "?")
            drs   = "DRS active" if int(info.get("drs", 0)) >= 10 else "DRS off"
            lap_n = info.get("lap", "?")
            driver_lines.append(
                f"  P{pos} {code}: Lap {lap_n}, "
                f"{spd:.0f} km/h, Gear {gear}, {drs}"
            )

        driver_summary = "\n".join(driver_lines)

        # If a specific driver is selected, add focused context
        focus = ""
        if self._selected_driver and self._selected_driver in drivers:
            d = drivers[self._selected_driver]
            focus = (
                f"\nFocus on {self._selected_driver}: "
                f"Position {d.get('position','?')}, "
                f"Lap {d.get('lap','?')}, "
                f"Speed {d.get('speed',0):.0f} km/h, "
                f"Gear {d.get('gear','?')}, "
                f"DRS {'active' if int(d.get('drs',0)) >= 10 else 'off'}."
            )

        prompt = f"""<s>[INST] You are an expert F1 race commentator and analyst.
Provide a short, insightful 2-3 sentence analysis of the current race situation.
Be specific about driver names, positions, and what might happen next.
Do not repeat yourself from previous commentary.

Current race situation:
- Lap: {lap} of {total}
- Race leader: {leader}
- Track status: {status}
- Top 10 drivers:
{driver_summary}{focus}

Give your analysis now: [/INST]"""

        return prompt

    def _trigger_commentary(self):
        """Ask the AI for commentary on the current telemetry."""
        if self._current_frame_data is None:
            self._append_commentary(
                "⏳ No telemetry data yet — start the race replay first.",
                color="#aaaaaa"
            )
            return

        # Don't start a new request if one is already running
        if self._worker and self._worker.isRunning():
            return

        self._last_commentary_time = time.time()
        self.ask_btn.setEnabled(False)
        self.status_label.setText("🤖 Asking AI...")
        self.status_label.setStyleSheet("color: #64b5f6;")

        prompt = self._build_prompt(self._current_frame_data)

        self._worker = AICommentaryWorker(self.client, prompt)
        self._worker.commentary_ready.connect(self._on_commentary_received)
        self._worker.error_occurred.connect(self._on_commentary_error)
        self._worker.start()

    def _on_commentary_received(self, text: str):
        """Called when the AI responds successfully."""
        lap_info = ""
        if self._current_frame_data:
            lap = self._current_frame_data.get(
                "session_data", {}
            ).get("lap", "?")
            lap_info = f"[Lap {lap}] "

        self._append_commentary(f"{lap_info}{text}", color="#f0f0f0")
        self.ask_btn.setEnabled(True)
        self.status_label.setText("✅ Commentary updated")
        self.status_label.setStyleSheet("color: green;")

    def _on_commentary_error(self, error_msg: str):
        """Called when the AI request fails."""
        self._append_commentary(f"⚠️ {error_msg}", color="#ff6b6b")
        self.ask_btn.setEnabled(True)
        self.status_label.setText("❌ AI request failed")
        self.status_label.setStyleSheet("color: red;")

    def _append_commentary(self, text: str, color: str = "#f0f0f0"):
        """Add a new commentary entry to the box."""
        timestamp = time.strftime("%H:%M:%S")
        html = (
            f'<p style="color:{color}; margin:4px 0;">'
            f'<span style="color:#888; font-size:9pt;">[{timestamp}]</span> '
            f'{text}</p>'
            f'<hr style="border:0; border-top:1px solid #333; margin:4px 0;">'
        )
        self.commentary_box.append(html)
        # Auto scroll to bottom
        sb = self.commentary_box.verticalScrollBar()
        sb.setValue(sb.maximum())
        self._commentary_history.append(text)

    def _clear_commentary(self):
        self.commentary_box.clear()
        self._commentary_history.clear()


def main():
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = F1AIAnalystWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()