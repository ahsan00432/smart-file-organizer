"""Modern graphical interface for the Smart File Organizer."""

from pathlib import Path
import queue
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import tempfile
import webbrowser

import customtkinter as ctk

import smart_file_organizer as organizer


class OrganizerApp(ctk.CTk):
    """Desktop application for manual and live file organization."""

    GITHUB_PROFILE = "https://github.com/ahsan00432"

    def __init__(self) -> None:
        super().__init__()

        self.title("Smart File Organizer")
        self.geometry("980x680")
        self.minsize(820, 560)
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        self.status_queue: queue.Queue[object] = queue.Queue()
        self.observer = None
        self.sweep_in_progress = False

        loaded_config = organizer.load_config(organizer.CONFIG_FILE)
        if loaded_config is None:
            self.folder = Path.home() / "Downloads"
            self.file_categories = {}
            self.settings = dict(organizer.DEFAULT_SETTINGS)
            self._config_error = "Could not load config.json. Check the terminal for details."
        else:
            self.folder, self.file_categories, self.settings = loaded_config
            self._config_error = ""

        self.folder_var = tk.StringVar(value=str(self.folder))
        self.monitor_var = tk.BooleanVar(value=False)
        self.activity_var = tk.StringVar(value="Ready")

        self.build_layout()
        self.after(100, self.drain_status_queue)

        if self._config_error:
            self.add_status(self._config_error)
        else:
            self.add_status("Ready to organize your folder.")

    def build_layout(self) -> None:
        """Create the application's visual layout."""
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=300, corner_radius=0, fg_color="#111827")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(9, weight=1)

        brand = ctk.CTkLabel(
            sidebar,
            text="SMART\nORGANIZER",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=27, weight="bold"),
            text_color="#f8fafc",
        )
        brand.grid(row=0, column=0, padx=30, pady=(38, 5), sticky="w")

        tagline = ctk.CTkLabel(
            sidebar,
            text="A calmer Downloads folder.\nSorted automatically, in real time.",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8",
        )
        tagline.grid(row=1, column=0, padx=30, pady=(0, 36), sticky="w")

        folder_label = ctk.CTkLabel(
            sidebar,
            text="FOLDER TO ORGANIZE",
            anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#64748b",
        )
        folder_label.grid(row=2, column=0, padx=30, pady=(0, 8), sticky="w")

        folder_entry = ctk.CTkEntry(
            sidebar,
            textvariable=self.folder_var,
            height=38,
            corner_radius=8,
            border_width=1,
            border_color="#334155",
            fg_color="#1e293b",
            text_color="#e2e8f0",
        )
        folder_entry.grid(row=3, column=0, padx=30, sticky="ew")
        folder_entry.configure(state="disabled")
        sidebar.grid_columnconfigure(0, weight=1)

        browse_button = ctk.CTkButton(
            sidebar,
            text="Browse for folder",
            command=self.choose_folder,
            height=36,
            corner_radius=8,
            fg_color="#263449",
            hover_color="#334155",
            text_color="#dbeafe",
        )
        browse_button.grid(row=4, column=0, padx=30, pady=(10, 28), sticky="ew")

        github_button = ctk.CTkButton(
            sidebar,
            text="View GitHub Profile",
            command=self.open_github_profile,
            height=34,
            corner_radius=8,
            fg_color="#1f2937",
            hover_color="#334155",
            text_color="#bfdbfe",
        )
        github_button.grid(row=5, column=0, padx=30, pady=(0, 20), sticky="ew")

        rate_button = ctk.CTkButton(
            sidebar,
            text="Rate on GitHub",
            command=self.rate_on_github,
            height=34,
            corner_radius=8,
            fg_color="#172554",
            hover_color="#1e3a8a",
            text_color="#bfdbfe",
        )
        rate_button.grid(row=6, column=0, padx=30, pady=(0, 20), sticky="ew")

        self.monitor_switch = ctk.CTkSwitch(
            sidebar,
            text="Enable Background Live-Monitoring",
            variable=self.monitor_var,
            command=self.toggle_monitoring,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e2e8f0",
            progress_color="#22c55e",
            button_color="#f8fafc",
            button_hover_color="#e2e8f0",
        )
        self.monitor_switch.grid(row=7, column=0, padx=30, pady=(0, 16), sticky="w")

        cache_button = ctk.CTkButton(
            sidebar,
            text="Clear System Temp Cache",
            command=self.clear_system_cache,
            height=34,
            corner_radius=8,
            fg_color="#3f1d2e",
            hover_color="#5b263c",
            text_color="#fecdd3",
        )
        cache_button.grid(row=8, column=0, padx=30, pady=(0, 18), sticky="ew")

        hint = ctk.CTkLabel(
            sidebar,
            text="Files are checked for stability before\nbeing moved, so downloads stay safe.",
            justify="left",
            anchor="sw",
            font=ctk.CTkFont(size=12),
            text_color="#64748b",
        )
        hint.grid(row=9, column=0, padx=30, pady=(0, 28), sticky="sw")

        content = ctk.CTkFrame(self, corner_radius=0, fg_color="#0b1120")
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(3, weight=1)

        heading = ctk.CTkLabel(
            content,
            text="Folder activity",
            anchor="w",
            font=ctk.CTkFont(size=31, weight="bold"),
            text_color="#f8fafc",
        )
        heading.grid(row=0, column=0, padx=40, pady=(42, 4), sticky="w")

        subheading = ctk.CTkLabel(
            content,
            text="Keep your files moving to the right place.",
            anchor="w",
            font=ctk.CTkFont(size=14),
            text_color="#94a3b8",
        )
        subheading.grid(row=1, column=0, padx=40, pady=(0, 28), sticky="w")

        action_row = ctk.CTkFrame(content, fg_color="transparent")
        action_row.grid(row=2, column=0, padx=40, sticky="ew")
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)

        self.clean_button = ctk.CTkButton(
            action_row,
            text="Clean Folder Now",
            command=self.clean_folder,
            height=52,
            corner_radius=10,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        )
        self.clean_button.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        manual_progress_label = ctk.CTkLabel(
            action_row,
            text="CURRENT FILE MOVE",
            anchor="w",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#64748b",
        )
        manual_progress_label.grid(row=1, column=0, padx=(0, 8), pady=(14, 5), sticky="w")

        self.manual_progress = ctk.CTkProgressBar(
            action_row,
            height=8,
            corner_radius=4,
            mode="indeterminate",
            progress_color="#3b82f6",
            fg_color="#1e293b",
        )
        self.manual_progress.grid(row=2, column=0, padx=(0, 8), sticky="ew")
        self.manual_progress.set(0)

        monitor_progress_label = ctk.CTkLabel(
            action_row,
            text="TOTAL SWEEP PROGRESS",
            anchor="w",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#64748b",
        )
        monitor_progress_label.grid(row=1, column=1, padx=(8, 0), pady=(14, 5), sticky="w")

        self.total_progress = ctk.CTkProgressBar(
            action_row,
            height=8,
            corner_radius=4,
            mode="indeterminate",
            progress_color="#22c55e",
            fg_color="#1e293b",
        )
        self.total_progress.grid(row=2, column=1, padx=(8, 0), sticky="ew")
        self.total_progress.set(0)

        status_card = ctk.CTkFrame(
            content,
            corner_radius=12,
            fg_color="#111827",
            border_width=1,
            border_color="#1e293b",
        )
        status_card.grid(row=3, column=0, padx=40, pady=(28, 40), sticky="nsew")
        status_card.grid_columnconfigure(0, weight=1)
        status_card.grid_rowconfigure(1, weight=1)

        status_header = ctk.CTkFrame(status_card, fg_color="transparent")
        status_header.grid(row=0, column=0, padx=20, pady=(17, 10), sticky="ew")
        status_header.grid_columnconfigure(0, weight=1)

        log_label = ctk.CTkLabel(
            status_header,
            text="ACTIVITY LOG",
            anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#64748b",
        )
        log_label.grid(row=0, column=0, sticky="w")

        self.status_badge = ctk.CTkLabel(
            status_header,
            textvariable=self.activity_var,
            width=90,
            height=24,
            corner_radius=12,
            fg_color="#172554",
            text_color="#93c5fd",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.status_badge.grid(row=0, column=1, sticky="e")

        self.status_box = ctk.CTkTextbox(
            status_card,
            corner_radius=8,
            border_width=0,
            fg_color="#0b1120",
            text_color="#cbd5e1",
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
        )
        self.status_box.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.status_box.configure(state="disabled")

    def choose_folder(self) -> None:
        """Let the user select a different folder for this session."""
        selected_folder = filedialog.askdirectory(
            title="Choose a folder to organize",
            initialdir=str(self.folder),
        )
        if selected_folder:
            self.stop_monitoring()
            self.folder = Path(selected_folder)
            self.folder_var.set(str(self.folder))
            self.settings["folder_to_organize"] = str(self.folder)
            self.add_status(f"Selected folder: {self.folder}")

    def open_github_profile(self) -> None:
        """Open the developer's GitHub profile in the default browser."""
        webbrowser.open(self.GITHUB_PROFILE)
        self.add_status(f"Opened GitHub profile: {self.GITHUB_PROFILE}")

    def rate_on_github(self) -> None:
        """Open the GitHub profile so users can star and rate the project."""
        webbrowser.open(self.GITHUB_PROFILE)
        self.add_status(f"Thanks for supporting the project: {self.GITHUB_PROFILE}")

    def clear_system_cache(self) -> None:
        """Remove accessible entries from the Windows temporary directory."""
        temporary_folder = Path(tempfile.gettempdir())
        confirmed = messagebox.askyesno(
            "Clear system temp cache",
            "This removes accessible files from the Windows temporary folder.\n\n"
            "Files currently in use will be skipped. Continue?",
            icon="warning",
        )
        if not confirmed:
            return

        removed_count = 0
        skipped_count = 0
        for item in temporary_folder.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                removed_count += 1
            except OSError:
                skipped_count += 1

        self.add_status(
            f"System temp cleanup complete: removed {removed_count}, "
            f"skipped {skipped_count}."
        )

    def clean_folder(self) -> None:
        """Start a manual sweep without blocking the GUI."""
        if self.sweep_in_progress:
            return
        if not self.folder.is_dir():
            self.add_status(f"Folder not found: {self.folder}")
            return

        self.sweep_in_progress = True
        self.clean_button.configure(state="disabled", text="Cleaning...")
        self.activity_var.set("Cleaning")
        self.manual_progress.start()
        threading.Thread(target=self.run_sweep, daemon=True).start()

    def run_sweep(self) -> None:
        """Run the existing organizer in a worker thread."""
        try:
            organizer.organize_folder(
                self.folder,
                self.file_categories,
                self.settings,
                organizer.CONFIG_FILE,
                status_callback=self.queue_status,
                progress_callback=self.queue_progress,
            )
            self.queue_status("Manual sweep complete.")
        except Exception as error:
            self.queue_status(f"Manual sweep failed: {error}")
        finally:
            self.status_queue.put("__SWEEP_FINISHED__")

    def toggle_monitoring(self) -> None:
        """Start or stop the watchdog observer from the switch."""
        if self.monitor_var.get():
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self) -> None:
        """Start the watchdog observer without blocking the GUI."""
        if self.observer is not None and self.observer.is_alive():
            return
        if not self.folder.is_dir():
            self.monitor_var.set(False)
            self.add_status(f"Folder not found: {self.folder}")
            return

        self.observer = organizer.create_observer(
            self.folder,
            self.file_categories,
            self.settings,
            organizer.CONFIG_FILE,
            status_callback=self.queue_status,
        )
        self.observer.start()
        self.activity_var.set("Monitoring")
        self.add_status(f"Live monitoring enabled: {self.folder}")

    def stop_monitoring(self) -> None:
        """Stop the watchdog observer if it is running."""
        if self.observer is None:
            return
        self.observer.stop()
        self.observer.join(timeout=2)
        self.observer = None
        self.monitor_var.set(False)
        self.activity_var.set("Ready")
        self.add_status("Live monitoring disabled.")

    def queue_status(self, message: str) -> None:
        """Queue worker-thread messages for safe display in Tk."""
        self.status_queue.put(message)

    def queue_progress(self, phase: str, current: int, total: int) -> None:
        """Queue per-file and total sweep progress for the Tk thread."""
        self.status_queue.put((phase, current, total))

    def drain_status_queue(self) -> None:
        """Display queued messages on the main Tk thread."""
        try:
            while True:
                message = self.status_queue.get_nowait()
                if isinstance(message, tuple) and len(message) == 3:
                    phase, current, total = message
                    if phase == "start":
                        self.manual_progress.start()
                    elif phase == "complete":
                        self.manual_progress.stop()
                        self.manual_progress.set(0)
                        self.total_progress.set(current / total if total else 0)
                    continue
                if message == "__SWEEP_FINISHED__":
                    self.sweep_in_progress = False
                    self.manual_progress.stop()
                    self.manual_progress.set(0)
                    self.clean_button.configure(state="normal", text="Clean Folder Now")
                    if not self.monitor_var.get():
                        self.activity_var.set("Ready")
                    continue
                self.add_status(message)
        except queue.Empty:
            pass
        self.after(100, self.drain_status_queue)

    def add_status(self, message: str) -> None:
        """Append one timestamp-free status line to the activity box."""
        self.status_box.configure(state="normal")
        self.status_box.insert("end", f"{message}\n")
        self.status_box.see("end")
        self.status_box.configure(state="disabled")

    def close_app(self) -> None:
        """Stop background monitoring before closing the window."""
        self.stop_monitoring()
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = OrganizerApp()
    app.mainloop()
