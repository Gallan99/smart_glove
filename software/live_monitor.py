"""Tkinter monitor for the five-channel constant-current AFE."""

from __future__ import annotations

import csv
import queue
import threading
import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
import serial
import serial.tools.list_ports
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from software.protocol import AFEFrame, compact_csv_header, compact_csv_row, parse_afe_row


BAUD_RATE = 115200
CHANNEL_COLORS = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00")


class SmartGloveMonitor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Pt-NP Smart Glove — Five-Channel Monitor")
        self.root.geometry("1180x760")
        self.root.minsize(980, 650)

        self.serial_port: serial.Serial | None = None
        self.reader: threading.Thread | None = None
        self.running = False
        self.events: queue.Queue[AFEFrame | Exception] = queue.Queue()
        self.log_handle = None
        self.log_writer = None

        self.times: deque[float] = deque(maxlen=600)
        self.values = [deque(maxlen=600) for _ in range(5)]
        self.current_vars = [tk.StringVar(value="—") for _ in range(5)]
        self.status_var = tk.StringVar(value="Disconnected")
        self.port_var = tk.StringVar()
        self.output_var = tk.StringVar(value=str(Path("measurements") / "session.csv"))

        self._build_ui()
        self.refresh_ports()
        self.root.after(50, self._drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        controls = ttk.LabelFrame(outer, text="Connection and logging", padding=10)
        controls.pack(fill="x")

        ttk.Label(controls, text="Serial port").grid(row=0, column=0, sticky="w")
        self.port_box = ttk.Combobox(controls, textvariable=self.port_var, state="readonly", width=14)
        self.port_box.grid(row=0, column=1, padx=(8, 4))
        ttk.Button(controls, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=4)

        ttk.Label(controls, text="Output CSV").grid(row=0, column=3, padx=(22, 0), sticky="w")
        ttk.Entry(controls, textvariable=self.output_var, width=45).grid(row=0, column=4, padx=8, sticky="ew")
        ttk.Button(controls, text="Browse", command=self.choose_output).grid(row=0, column=5, padx=4)

        self.start_button = ttk.Button(controls, text="Start", command=self.start)
        self.start_button.grid(row=0, column=6, padx=(18, 4))
        self.stop_button = ttk.Button(controls, text="Stop", command=self.stop, state="disabled")
        self.stop_button.grid(row=0, column=7, padx=4)
        controls.columnconfigure(4, weight=1)

        summary = ttk.Frame(outer, padding=(0, 12, 0, 8))
        summary.pack(fill="x")
        for sensor_id in range(5):
            card = ttk.LabelFrame(summary, text=f"S{sensor_id}", padding=8)
            card.grid(row=0, column=sensor_id, padx=(0, 8), sticky="ew")
            ttk.Label(card, textvariable=self.current_vars[sensor_id], font=("Segoe UI", 13, "bold")).pack()
            ttk.Label(card, text="MΩ").pack()
            summary.columnconfigure(sensor_id, weight=1)

        ttk.Label(summary, textvariable=self.status_var, anchor="e").grid(
            row=0, column=5, padx=(12, 0), sticky="e"
        )

        plot_frame = ttk.Frame(outer)
        plot_frame.pack(fill="both", expand=True)
        self.figure, self.axis = plt.subplots(figsize=(10, 5.5), dpi=100)
        self.lines = []
        for sensor_id, color in enumerate(CHANNEL_COLORS):
            (line,) = self.axis.plot([], [], color=color, linewidth=1.5, label=f"S{sensor_id}")
            self.lines.append(line)
        self.axis.set_title("Filtered sensor resistance")
        self.axis.set_xlabel("Time (s)")
        self.axis.set_ylabel("Resistance (MΩ)")
        self.axis.grid(True, linestyle="--", alpha=0.35)
        self.axis.legend(ncol=5, loc="upper center")

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        NavigationToolbar2Tk(self.canvas, plot_frame).update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def refresh_ports(self) -> None:
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_box["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])

    def choose_output(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="Save compact sensor log",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self.output_var.set(selected)

    def start(self) -> None:
        port = self.port_var.get()
        if not port:
            messagebox.showwarning("Serial port", "Select a serial port first.")
            return

        try:
            output = Path(self.output_var.get()).expanduser()
            output.parent.mkdir(parents=True, exist_ok=True)
            self.log_handle = output.open("w", newline="", encoding="utf-8")
            self.log_writer = csv.writer(self.log_handle)
            self.log_writer.writerow(compact_csv_header())
            self.serial_port = serial.Serial(port, BAUD_RATE, timeout=1)
            self.serial_port.reset_input_buffer()
        except Exception as exc:
            if self.log_handle:
                self.log_handle.close()
            self.log_handle = None
            messagebox.showerror("Unable to start", str(exc))
            return

        self.times.clear()
        for channel in self.values:
            channel.clear()
        self.running = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set(f"Connected to {port} at {BAUD_RATE} bit/s")
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

    def _read_loop(self) -> None:
        assert self.serial_port is not None
        while self.running and self.serial_port.is_open:
            try:
                raw = self.serial_port.readline().decode("utf-8", errors="ignore")
                frame = parse_afe_row(raw)
                if frame is not None:
                    self.events.put(frame)
            except Exception as exc:
                self.events.put(exc)
                break

    def _drain_events(self) -> None:
        updated = False
        try:
            while True:
                event = self.events.get_nowait()
                if isinstance(event, Exception):
                    self.status_var.set(f"Read error: {event}")
                    self.stop()
                    break
                self._accept_frame(event)
                updated = True
        except queue.Empty:
            pass

        if updated:
            self._redraw()
        self.root.after(50, self._drain_events)

    def _accept_frame(self, frame: AFEFrame) -> None:
        if not frame.is_valid:
            self.status_var.set("Frame received with an invalid sensor value")
            return
        self.times.append(frame.time_ms / 1000.0)
        for sensor_id, value in enumerate(frame.filtered_mohm):
            self.values[sensor_id].append(value)
            self.current_vars[sensor_id].set(f"{value:.3f}")
        if self.log_writer:
            self.log_writer.writerow(compact_csv_row(frame))
            self.log_handle.flush()

    def _redraw(self) -> None:
        x = list(self.times)
        for sensor_id, line in enumerate(self.lines):
            line.set_data(x, list(self.values[sensor_id]))
        self.axis.relim()
        self.axis.autoscale_view()
        self.canvas.draw_idle()

    def stop(self) -> None:
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = None
        if self.log_handle:
            self.log_handle.close()
        self.log_handle = None
        self.log_writer = None
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        if not self.status_var.get().startswith("Read error"):
            self.status_var.set("Disconnected")

    def close(self) -> None:
        self.stop()
        plt.close(self.figure)
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    SmartGloveMonitor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
