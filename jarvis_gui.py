"""Futuristic dark Tkinter desktop interface for JARVIS's existing backend."""

import queue
import threading
import tkinter as tk
import logging
from datetime import datetime
from tkinter import scrolledtext, ttk

from assistant_backend import AssistantBackend
from voice_service import VoiceService


LOGGER = logging.getLogger(__name__)

THEME = {"background": "#070B14", "surface": "#0D1525", "surface_alt": "#111D31", "border": "#263B59", "accent": "#37D7FF", "accent_dim": "#167A9B", "green": "#40E0A5", "text": "#E6F3FF", "muted": "#91A8BF", "user": "#9CB8FF", "warning": "#FFC857"}


def system_metric_value(label, report):
    """Extract the useful portion of a backend system report for a compact card."""
    prefix = f"{label} usage is "
    return report[len(prefix):].rstrip(".") if report.startswith(prefix) else report.rstrip(".")


class JarvisGUI(tk.Tk):
    """A responsive desktop shell; all backend and voice work stays off the UI thread."""

    def __init__(self, backend=None, voice_service=None):
        super().__init__()
        self.backend = backend or AssistantBackend()
        self.voice_service = voice_service or VoiceService()
        self.work_queue = queue.Queue()
        self.title("JARVIS // Desktop Console")
        self.geometry("1120x760")
        self.minsize(820, 580)
        self.configure(background=THEME["background"])
        self.status_var = tk.StringVar(value="CONNECTING")
        self.activity_var = tk.StringVar(value="STANDING BY")
        self.clock_var = tk.StringVar()
        self.metric_vars = {label: tk.StringVar(value="Loading...") for label in ("CPU", "RAM", "Disk")}
        self._configure_styles()
        self._build_interface()
        self.after(100, self._poll_workers)
        self._update_clock()
        self._refresh_status()
        self._refresh_system_information()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.Vertical.TScrollbar", background=THEME["surface_alt"], troughcolor=THEME["surface"], bordercolor=THEME["border"], arrowcolor=THEME["text"])

    def _build_interface(self):
        shell = tk.Frame(self, bg=THEME["background"], padx=24, pady=20)
        shell.grid(sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=4)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)
        self._build_header(shell)
        self._build_conversation_panel(shell)
        self._build_system_panel(shell)
        self._build_input_panel(shell)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=THEME["surface"], highlightbackground=THEME["border"], highlightthickness=1)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        header.columnconfigure(1, weight=1)
        identity = tk.Frame(header, bg=THEME["surface"], padx=18, pady=14)
        identity.grid(row=0, column=0, sticky="w")
        tk.Label(identity, text="J.A.R.V.I.S", bg=THEME["surface"], fg=THEME["accent"], font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(identity, text="LOCAL INTELLIGENCE INTERFACE", bg=THEME["surface"], fg=THEME["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 0))
        status_area = tk.Frame(header, bg=THEME["surface"], padx=18, pady=14)
        status_area.grid(row=0, column=2, sticky="e")
        self.status_dot = tk.Label(status_area, text="●", bg=THEME["surface"], fg=THEME["warning"], font=("Segoe UI", 14))
        self.status_dot.grid(row=0, column=0, padx=(0, 6))
        tk.Label(status_area, textvariable=self.status_var, bg=THEME["surface"], fg=THEME["text"], font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w")
        tk.Label(status_area, textvariable=self.clock_var, bg=THEME["surface"], fg=THEME["muted"], font=("Consolas", 10)).grid(row=1, column=0, columnspan=2, sticky="e", pady=(4, 0))

    def _build_conversation_panel(self, parent):
        panel = tk.Frame(parent, bg=THEME["surface"], highlightbackground=THEME["border"], highlightthickness=1)
        panel.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)
        panel_header = tk.Frame(panel, bg=THEME["surface"], padx=16, pady=12)
        panel_header.grid(row=0, column=0, sticky="ew")
        tk.Label(panel_header, text="CONVERSATION", bg=THEME["surface"], fg=THEME["text"], font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        tk.Label(panel_header, textvariable=self.activity_var, bg=THEME["surface"], fg=THEME["accent"], font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT)
        self.history = scrolledtext.ScrolledText(panel, wrap=tk.WORD, state=tk.DISABLED, bg=THEME["background"], fg=THEME["text"], insertbackground=THEME["accent"], borderwidth=0, highlightthickness=0, padx=18, pady=16, font=("Segoe UI", 11), selectbackground=THEME["accent_dim"])
        self.history.grid(row=1, column=0, sticky="nsew")
        self.history.vbar.configure(
    bg="#0b1f2a",
    activebackground="#00d9ff",
    troughcolor="#071018",
    highlightthickness=0,
)
        self.history.tag_configure("user_label", foreground=THEME["user"], font=("Segoe UI", 9, "bold"), justify="right")
        self.history.tag_configure("user_message", foreground=THEME["text"], justify="right", spacing3=16)
        self.history.tag_configure("jarvis_label", foreground=THEME["accent"], font=("Segoe UI", 9, "bold"))
        self.history.tag_configure("jarvis_message", foreground=THEME["text"], spacing3=16)
        self.history.tag_configure("notice", foreground=THEME["warning"], font=("Segoe UI", 9, "italic"), spacing3=10)

    def _build_system_panel(self, parent):
        sidebar = tk.Frame(parent, bg=THEME["background"])
        sidebar.grid(row=1, column=1, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        tk.Label(sidebar, text="SYSTEM STATUS", bg=THEME["background"], fg=THEME["muted"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        for row, (label, variable) in enumerate(self.metric_vars.items(), start=1):
            card = tk.Frame(sidebar, bg=THEME["surface"], highlightbackground=THEME["border"], highlightthickness=1, padx=14, pady=14)
            card.grid(row=row, column=0, sticky="ew", pady=(0, 10))
            tk.Label(card, text=label, bg=THEME["surface"], fg=THEME["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(card, textvariable=variable, bg=THEME["surface"], fg=THEME["text"], font=("Segoe UI", 10), wraplength=180, justify=tk.LEFT).pack(anchor="w", pady=(7, 0))
        tk.Button(sidebar, text="↻  REFRESH", command=self._refresh_system_information, bg=THEME["surface_alt"], fg=THEME["text"], activebackground=THEME["accent_dim"], activeforeground=THEME["text"], relief=tk.FLAT, padx=12, pady=8, font=("Segoe UI", 9, "bold"), cursor="hand2").grid(row=4, column=0, sticky="ew", pady=(2, 0))

    def _build_input_panel(self, parent):
        input_panel = tk.Frame(parent, bg=THEME["surface"], highlightbackground=THEME["border"], highlightthickness=1, padx=14, pady=14)
        input_panel.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        input_panel.columnconfigure(0, weight=1)
        self.input_box = tk.Entry(input_panel, bg=THEME["background"], fg=THEME["text"], insertbackground=THEME["accent"], relief=tk.FLAT, highlightthickness=1, highlightbackground=THEME["border"], highlightcolor=THEME["accent"], font=("Segoe UI", 11))
        self.input_box.grid(row=0, column=0, sticky="ew", ipady=11, padx=(0, 10))
        self.input_box.bind("<Return>", lambda _event: self.submit_text())
        self.send_button = tk.Button(input_panel, text="SEND", command=self.submit_text, bg=THEME["accent"], fg=THEME["background"], activebackground="#7BE9FF", activeforeground=THEME["background"], relief=tk.FLAT, padx=18, pady=10, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.send_button.grid(row=0, column=1, padx=(0, 8))
        self.listen_button = tk.Button(input_panel, text="◉  LISTEN", command=self.listen, bg=THEME["surface_alt"], fg=THEME["accent"], activebackground=THEME["accent_dim"], activeforeground=THEME["text"], relief=tk.FLAT, highlightthickness=1, highlightbackground=THEME["accent_dim"], padx=18, pady=10, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.listen_button.grid(row=0, column=2, padx=(0, 8))
        tk.Button(input_panel, text="CLEAR", command=self.clear_conversation, bg=THEME["surface_alt"], fg=THEME["muted"], activebackground=THEME["border"], activeforeground=THEME["text"], relief=tk.FLAT, padx=12, pady=10, font=("Segoe UI", 9, "bold"), cursor="hand2").grid(row=0, column=3)

    def submit_text(self):
        user_input = self.input_box.get().strip()
        if not user_input:
            return
        self.input_box.delete(0, tk.END)
        self._append("You", user_input)
        self._set_activity("THINKING...", "JARVIS is processing locally")
        self._run_in_background(
            self.backend.process, user_input, callback=self._handle_reply
        )

    def listen(self):
        self._set_activity("LISTENING...", "Voice capture is active")
        self._run_in_background(self.voice_service.listen, callback=self._handle_voice_result)

    def clear_conversation(self):
        self.backend.clear_conversation()
        self.history.configure(state=tk.NORMAL)
        self.history.delete("1.0", tk.END)
        self.history.configure(state=tk.DISABLED)
        self._append("JARVIS", "Conversation cleared. Saved memories were kept.")
        self._set_activity("STANDING BY")

    def _refresh_status(self):
        self._run_in_background(self.backend.check_online, callback=self._set_online_status)

    def _refresh_system_information(self):
        self._run_in_background(self.backend.get_system_information, callback=self._set_system_information)

    def _run_in_background(self, function, *args, callback=None):
        def worker():
            try:
                result = function(*args)
                self.work_queue.put((callback, result, None))
            except Exception as error:
                LOGGER.exception("JARVIS GUI background task failed")
                self.work_queue.put((callback, None, error))
        threading.Thread(target=worker, daemon=True).start()

    def _poll_workers(self):
        try:
            while True:
                callback, result, error = self.work_queue.get_nowait()
                if callback:
                    callback(result, error)
        except queue.Empty:
            pass
        self.after(100, self._poll_workers)

    def _handle_reply(self, reply, error):
        if error:
            self._append("JARVIS", f"Unexpected error: {error}")
        else:
            for notice in reply.notices:
                self._append("NOTICE", notice)
            self._append("JARVIS", reply.message)
            self._run_in_background(self.voice_service.speak, reply.message)
            if reply.should_exit:
                self.destroy()
                return
        self._set_activity("STANDING BY")
        self._refresh_status()

    def _handle_voice_result(self, result, error):
        if error or result.error:
            self._append("JARVIS", result.error if result else f"Voice error: {error}")
            self._set_activity("STANDING BY")
            self._refresh_status()
            return
        self.input_box.insert(0, result.text)
        self.submit_text()

    def _set_online_status(self, online, error):
        if online and not error:
            self.status_var.set("ONLINE // LOCAL OLLAMA")
            self.status_dot.configure(fg=THEME["green"])
        else:
            self.status_var.set("OFFLINE // START OLLAMA")
            self.status_dot.configure(fg=THEME["warning"])

    def _set_system_information(self, information, error):
        if error:
            for variable in self.metric_vars.values():
                variable.set("Unavailable")
            return
        for label, variable in self.metric_vars.items():
            variable.set(system_metric_value(label, information.get(label, "Unavailable")))

    def _set_activity(self, activity, notice=None):
        self.activity_var.set(activity)
        if notice:
            self._append("NOTICE", notice)

    def _update_clock(self):
        self.clock_var.set(datetime.now().strftime("%H:%M:%S  //  %d %b %Y"))
        self.after(1000, self._update_clock)

    def _append(self, speaker, message):
        tag_prefix = "user" if speaker == "You" else "notice" if speaker == "NOTICE" else "jarvis"
        label = "YOU" if speaker == "You" else "SYSTEM" if speaker == "NOTICE" else "JARVIS"
        self.history.configure(state=tk.NORMAL)
        label_tag = f"{tag_prefix}_label" if tag_prefix != "notice" else "notice"
        message_tag = f"{tag_prefix}_message" if tag_prefix != "notice" else "notice"
        self.history.insert(tk.END, f"{label}\n", label_tag)
        self.history.insert(tk.END, f"{message}\n\n", message_tag)
        self.history.configure(state=tk.DISABLED)
        self.history.see(tk.END)


def main():
    JarvisGUI().mainloop()


if __name__ == "__main__":
    main()
