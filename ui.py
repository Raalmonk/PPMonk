import threading
import queue
import customtkinter as ctk

from main import run_simulation, SCENARIO_MAP


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


def _crit_percent_to_rating(percent):
    base = 0.10
    return max(0, (percent / 100 - base) * 4600)


def _haste_percent_to_rating(percent):
    return max(0, (percent / 100) * 4400)


def _vers_percent_to_rating(percent):
    return max(0, (percent / 100) * 5400)


def _mastery_percent_to_rating(percent):
    base = 0.19
    target = max(percent / 100 - base, 0)
    dr_threshold = 1380
    eff_rating = target * 2000
    if eff_rating <= dr_threshold:
        return eff_rating
    return dr_threshold + (eff_rating - dr_threshold) / 0.9


class PPMonkApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PPMonk AI Simulator")
        self.geometry("1200x780")
        self.minsize(1100, 720)

        self.log_queue = queue.Queue()
        self.running = False

        self.status_var = ctk.StringVar(value="Ready")
        self.total_ap_var = ctk.StringVar(value="--")
        self.scenario_var = ctk.StringVar(value="Patchwerk")

        self._build_layout()
        self.after(100, self._process_log_queue)

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure((1, 2, 3, 4, 5, 6), weight=0)
        sidebar.grid_rowconfigure(7, weight=1)

        title = ctk.CTkLabel(
            sidebar,
            text="PPMonk AI Simulator",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.stat_vars = {
            "Haste": ctk.DoubleVar(value=15.0),
            "Crit": ctk.DoubleVar(value=25.0),
            "Mastery": ctk.DoubleVar(value=40.0),
            "Versatility": ctk.DoubleVar(value=10.0),
        }
        stat_ranges = {
            "Haste": (0, 50),
            "Crit": (0, 50),
            "Mastery": (0, 100),
            "Versatility": (0, 30),
        }

        for idx, (name, var) in enumerate(self.stat_vars.items(), start=1):
            frame = ctk.CTkFrame(sidebar)
            frame.grid(row=idx, column=0, padx=20, pady=6, sticky="ew")
            frame.grid_columnconfigure(1, weight=1)

            label = ctk.CTkLabel(frame, text=f"{name}")
            label.grid(row=0, column=0, padx=(8, 4), pady=8, sticky="w")

            slider = ctk.CTkSlider(
                frame,
                from_=stat_ranges[name][0],
                to=stat_ranges[name][1],
                variable=var,
                number_of_steps=stat_ranges[name][1],
                command=lambda _=None, n=name: self._update_stat_entry(n),
            )
            slider.grid(row=0, column=1, padx=(4, 6), pady=8, sticky="ew")

            entry = ctk.CTkEntry(frame, width=70)
            entry.grid(row=0, column=2, padx=(4, 8), pady=8)
            entry.insert(0, f"{var.get():.1f}")
            entry.bind("<FocusOut>", lambda event, n=name: self._sync_entry_to_var(event, n))
            entry.bind("<Return>", lambda event, n=name: self._sync_entry_to_var(event, n))
            setattr(self, f"{name.lower()}_entry", entry)

        talents_label = ctk.CTkLabel(sidebar, text="Talents", font=ctk.CTkFont(weight="bold"))
        talents_label.grid(row=5, column=0, padx=20, pady=(16, 4), sticky="w")

        self.talent_vars = {
            "WDP": ctk.BooleanVar(value=True),
            "SW": ctk.BooleanVar(value=True),
            "Ascension": ctk.BooleanVar(value=True),
        }

        for i, (talent, var) in enumerate(self.talent_vars.items(), start=6):
            chk = ctk.CTkCheckBox(sidebar, text=talent, variable=var)
            chk.grid(row=i, column=0, padx=20, pady=4, sticky="w")

        scenario_label = ctk.CTkLabel(sidebar, text="Scenario", font=ctk.CTkFont(weight="bold"))
        scenario_label.grid(row=9, column=0, padx=20, pady=(16, 4), sticky="w")

        scenario_menu = ctk.CTkOptionMenu(
            sidebar,
            values=list(SCENARIO_MAP.keys()),
            variable=self.scenario_var,
        )
        scenario_menu.grid(row=10, column=0, padx=20, pady=6, sticky="ew")

        start_btn = ctk.CTkButton(
            sidebar,
            text="Start Simulation",
            fg_color="#1b8f61",
            hover_color="#146645",
            command=self._start_simulation,
        )
        start_btn.grid(row=11, column=0, padx=20, pady=20, sticky="ew")
        self.start_button = start_btn

        main = ctk.CTkFrame(self)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        status_frame = ctk.CTkFrame(main)
        status_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        status_frame.grid_columnconfigure(1, weight=1)

        status_label = ctk.CTkLabel(status_frame, textvariable=self.status_var, font=ctk.CTkFont(size=16, weight="bold"))
        status_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.progress = ctk.CTkProgressBar(status_frame, mode="determinate")
        self.progress.set(0)
        self.progress.grid(row=0, column=1, padx=10, pady=12, sticky="ew")

        log_label = ctk.CTkLabel(main, text="Combat Log", font=ctk.CTkFont(weight="bold"))
        log_label.grid(row=1, column=0, padx=20, pady=(6, 4), sticky="w")

        self.log_box = ctk.CTkTextbox(main, font=("Consolas", 12), state="disabled")
        self.log_box.grid(row=2, column=0, padx=20, pady=(0, 12), sticky="nsew")

        ap_frame = ctk.CTkFrame(main)
        ap_frame.grid(row=3, column=0, padx=20, pady=(4, 20), sticky="ew")
        ap_frame.grid_columnconfigure(1, weight=1)

        ap_label = ctk.CTkLabel(ap_frame, text="Total AP", font=ctk.CTkFont(size=18, weight="bold"))
        ap_label.grid(row=0, column=0, padx=10, pady=12, sticky="w")

        self.ap_value_label = ctk.CTkLabel(ap_frame, textvariable=self.total_ap_var, font=ctk.CTkFont(size=26, weight="bold"))
        self.ap_value_label.grid(row=0, column=1, padx=10, pady=12, sticky="e")

    def _update_stat_entry(self, name):
        entry = getattr(self, f"{name.lower()}_entry")
        var = self.stat_vars[name]
        entry.delete(0, "end")
        entry.insert(0, f"{var.get():.1f}")

    def _sync_entry_to_var(self, event, name):
        entry = getattr(self, f"{name.lower()}_entry")
        try:
            val = float(entry.get())
            min_v, max_v = {
                "Haste": (0, 50),
                "Crit": (0, 50),
                "Mastery": (0, 100),
                "Versatility": (0, 30),
            }[name]
            val = max(min_v, min(max_v, val))
            self.stat_vars[name].set(val)
            entry.delete(0, "end")
            entry.insert(0, f"{val:.1f}")
        except ValueError:
            entry.delete(0, "end")
            entry.insert(0, f"{self.stat_vars[name].get():.1f}")

    def _append_log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _start_simulation(self):
        if self.running:
            return
        self.running = True
        self.total_ap_var.set("--")
        self.status_var.set("Training...")
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        self.start_button.configure(state="disabled")

        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        stats = {name: var.get() for name, var in self.stat_vars.items()}
        talents = [talent for talent, var in self.talent_vars.items() if var.get()]
        scenario = self.scenario_var.get()

        ratings = {
            "haste_rating": _haste_percent_to_rating(stats["Haste"]),
            "crit_rating": _crit_percent_to_rating(stats["Crit"]),
            "mastery_rating": _mastery_percent_to_rating(stats["Mastery"]),
            "vers_rating": _vers_percent_to_rating(stats["Versatility"]),
        }

        thread = threading.Thread(
            target=self._run_worker,
            args=(ratings, talents, scenario),
            daemon=True,
        )
        thread.start()

    def _run_worker(self, ratings, talents, scenario):
        try:
            result = run_simulation(
                talents=talents if talents else None,
                scenario_name=scenario,
                log_callback=self._enqueue_log,
                status_callback=self._enqueue_status,
                **ratings,
            )
            self.log_queue.put(("result", result))
        finally:
            self.log_queue.put(("status", {"text": "Complete", "progress": 1.0, "stop": True}))

    def _enqueue_log(self, message):
        self.log_queue.put(("log", message))

    def _enqueue_status(self, text, progress=None):
        self.log_queue.put(("status", {"text": text, "progress": progress}))

    def _process_log_queue(self):
        while not self.log_queue.empty():
            item_type, payload = self.log_queue.get()
            if item_type == "log":
                self._append_log(payload)
            elif item_type == "status":
                self.status_var.set(payload.get("text", ""))
                if payload.get("progress") is not None:
                    self.progress.configure(mode="determinate")
                    self.progress.stop()
                    self.progress.set(payload["progress"])
                if payload.get("stop"):
                    self.progress.stop()
                    self.progress.configure(mode="determinate")
                    self.progress.set(1.0)
                    self.start_button.configure(state="normal")
                    self.running = False
            elif item_type == "result":
                if payload:
                    self.total_ap_var.set(f"{payload.get('total_ap', 0):,.2f}")
        self.after(100, self._process_log_queue)


def main():
    app = PPMonkApp()
    app.mainloop()


if __name__ == "__main__":
    main()
