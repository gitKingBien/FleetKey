"""
FleetKey floating shortcuts app for Windows.

Features:
- Always-on-top floating window
- Adjustable opacity
- Expand/collapse shortcut list with persisted state
- Scrollable shortcuts list for larger sets
- Click shortcuts to open files, folders, and URLs
- Right-click context menu for extra options
"""

from __future__ import annotations

import json
import os
import re
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import tkinter as tk
from tkinter import messagebox


APP_NAME = "FleetKey"
CONFIG_PATH = Path(__file__).with_name("shortcuts.json")

MIN_OPACITY = 0.3
MAX_OPACITY = 1.0
MIN_WIDTH = 280
MIN_EXPANDED_HEIGHT = 220
DEFAULT_GEOMETRY = "340x420+60+60"
DEFAULT_COLLAPSED_GEOMETRY = "340x56+60+60"
COLLAPSED_HEIGHT = 56

GEOMETRY_RE = re.compile(
    r"^(?P<w>\d+)x(?P<h>\d+)(?P<x>[+-]\d+)(?P<y>[+-]\d+)$",
)

UI_COLORS = {
    "outer_bg": "#5a5a5a",
    "outer_border": "#3f3f3f",
    "text": "#f0f0f0",
    "button_bg": "#6a6a6a",
    "button_active_bg": "#7a7a7a",
    "scale_trough": "#7d7d7d",
}

DEFAULT_CONFIG = {
    "opacity": 0.92,
    "geometry": DEFAULT_GEOMETRY,
    "expanded_geometry": DEFAULT_GEOMETRY,
    "collapsed_geometry": DEFAULT_COLLAPSED_GEOMETRY,
    "is_collapsed": False,
    "shortcuts": [
        {
            "label": "Open Sample PDF",
            "target": r"C:\Users\Public\Documents\Sample.pdf",
        },
        {"label": "Open YouTube", "target": "https://www.youtube.com"},
        {"label": "Open Downloads", "target": r"%USERPROFILE%\Downloads"},
    ],
}


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp numeric value to a min and max range."""
    return max(min_value, min(max_value, value))


def parse_geometry(geometry: str) -> tuple[int, int, int, int] | None:
    """Parse geometry string in the format `wxh+x+y`."""
    match = GEOMETRY_RE.fullmatch(geometry)
    if match is None:
        return None
    return (
        int(match.group("w")),
        int(match.group("h")),
        int(match.group("x")),
        int(match.group("y")),
    )


def build_geometry(width: int, height: int, x: int, y: int) -> str:
    """Build a Tk geometry string."""
    return f"{width}x{height}+{x}+{y}"


def normalize_geometry(
    value: Any,
    fallback: str,
    *,
    min_width: int = MIN_WIDTH,
    min_height: int = MIN_EXPANDED_HEIGHT,
) -> str:
    """Normalize a geometry value and enforce minimum width/height."""
    parsed = parse_geometry(value) if isinstance(value, str) else None
    if parsed is None:
        parsed = parse_geometry(fallback)
    if parsed is None:
        parsed = (min_width, min_height, 60, 60)

    width, height, x, y = parsed
    return build_geometry(max(min_width, width), max(min_height, height), x, y)


def normalize_collapsed_geometry(value: Any, fallback: str) -> str:
    """Normalize collapsed geometry with fixed collapsed height."""
    parsed = parse_geometry(value) if isinstance(value, str) else None
    if parsed is None:
        parsed = parse_geometry(fallback)
    if parsed is None:
        parsed = (MIN_WIDTH, COLLAPSED_HEIGHT, 60, 60)

    width, _, x, y = parsed
    return build_geometry(max(MIN_WIDTH, width), COLLAPSED_HEIGHT, x, y)


def sanitize_config(data: dict[str, Any]) -> dict[str, Any]:
    """Return validated config with safe defaults."""
    opacity = data.get("opacity", DEFAULT_CONFIG["opacity"])
    if not isinstance(opacity, (int, float)):
        opacity = DEFAULT_CONFIG["opacity"]
    safe_opacity = clamp(float(opacity), MIN_OPACITY, MAX_OPACITY)

    is_collapsed = bool(data.get("is_collapsed", False))

    expanded_geometry = normalize_geometry(
        data.get("expanded_geometry", DEFAULT_GEOMETRY),
        DEFAULT_GEOMETRY,
        min_width=MIN_WIDTH,
        min_height=MIN_EXPANDED_HEIGHT,
    )
    collapsed_geometry = normalize_collapsed_geometry(
        data.get("collapsed_geometry", DEFAULT_COLLAPSED_GEOMETRY),
        DEFAULT_COLLAPSED_GEOMETRY,
    )
    geometry_source = data.get("geometry")
    if is_collapsed:
        geometry = normalize_collapsed_geometry(
            geometry_source,
            collapsed_geometry,
        )
    else:
        geometry = normalize_geometry(
            geometry_source,
            expanded_geometry,
            min_width=MIN_WIDTH,
            min_height=MIN_EXPANDED_HEIGHT,
        )

    shortcuts_data = data.get("shortcuts", [])
    if not isinstance(shortcuts_data, list):
        shortcuts_data = []

    safe_shortcuts: list[dict[str, str]] = []
    for item in shortcuts_data:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        target = item.get("target")
        if not isinstance(label, str) or not isinstance(target, str):
            continue
        label = label.strip()
        target = target.strip()
        if label and target:
            safe_shortcuts.append({"label": label, "target": target})

    return {
        "opacity": safe_opacity,
        "geometry": geometry,
        "expanded_geometry": expanded_geometry,
        "collapsed_geometry": collapsed_geometry,
        "is_collapsed": is_collapsed,
        "shortcuts": safe_shortcuts,
    }


def save_config(config: dict[str, Any]) -> None:
    """Atomically write config to avoid partial/corrupt saves."""
    safe_config = sanitize_config(config)
    temp_path = CONFIG_PATH.with_suffix(".json.tmp")
    payload = json.dumps(safe_config, indent=2)
    try:
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, CONFIG_PATH)
    finally:
        temp_path.unlink(missing_ok=True)


def load_config() -> dict[str, Any]:
    """Load config from disk and sanitize values."""
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return sanitize_config(DEFAULT_CONFIG.copy())

    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        messagebox.showwarning(
            APP_NAME,
            "Could not parse shortcuts.json. Loading default config.",
        )
        return sanitize_config(DEFAULT_CONFIG.copy())

    if not isinstance(raw, dict):
        return sanitize_config(DEFAULT_CONFIG.copy())
    return sanitize_config(raw)


def resolve_target(raw_target: str) -> str:
    """Expand environment variables and home shorthand in file paths."""
    expanded = os.path.expandvars(raw_target)
    expanded = os.path.expanduser(expanded)
    return expanded


def is_http_url(value: str) -> bool:
    """Return True only for valid HTTP(S) URLs."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def open_target(target: str) -> None:
    """Open a URL in browser or a path using the Windows default handler."""
    raw_target = target.strip()
    if is_http_url(raw_target):
        webbrowser.open(raw_target, new=2)
        return

    resolved = resolve_target(raw_target)
    if not Path(resolved).exists():
        messagebox.showerror(APP_NAME, f"Path not found:\n{resolved}")
        return

    os.startfile(resolved)  # type: ignore[attr-defined]


class FloatingShortcutsApp:
    """Main Tkinter application for FleetKey."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.config = load_config()
        self.is_collapsed = bool(self.config.get("is_collapsed", False))

        self.root.title(APP_NAME)
        self.root.geometry(self.config["geometry"])
        self.root.minsize(MIN_WIDTH, COLLAPSED_HEIGHT)
        self.root.resizable(True, True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.config["opacity"])

        self.opacity_var = tk.DoubleVar(value=self.config["opacity"])
        self.content_frame: tk.Frame | None = None
        self.opacity_row: tk.Frame | None = None
        self.opacity_label: tk.Label | None = None
        self.controls_frame: tk.Frame | None = None
        self.opacity_scale: tk.Scale | None = None
        self.toggle_button: tk.Button | None = None
        self.shortcut_container: tk.Frame | None = None
        self.shortcut_canvas: tk.Canvas | None = None
        self.shortcut_inner_frame: tk.Frame | None = None
        self.shortcut_window_id: int | None = None
        self.context_menu: tk.Menu | None = None
        self._save_after_id: str | None = None
        self._last_saved_state: tuple[str, float, bool] | None = None

        self._build_ui()
        self._build_context_menu()
        self._render_shortcuts()
        self._apply_collapsed_layout()
        self._last_saved_state = self._current_save_state()

        self.root.bind("<Configure>", self._on_window_configure)
        self.root.bind_all("<Button-3>", self._show_context_menu, add="+")
        self.root.bind("<Escape>", lambda _: self.root.destroy())

    def _build_ui(self) -> None:
        wrapper = tk.Frame(
            self.root,
            bg=UI_COLORS["outer_bg"],
            highlightthickness=1,
            highlightbackground=UI_COLORS["outer_border"],
        )
        wrapper.pack(fill="both", expand=True)

        self.content_frame = tk.Frame(wrapper, bg=UI_COLORS["outer_bg"])
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.opacity_row = tk.Frame(
            self.content_frame,
            bg=UI_COLORS["outer_bg"],
        )
        self.opacity_row.pack(fill="x", pady=(0, 10))

        self.controls_frame = tk.Frame(
            self.opacity_row,
            bg=UI_COLORS["outer_bg"],
        )
        self.controls_frame.pack(fill="x")
        self.controls_frame.grid_columnconfigure(1, weight=1)
        self.controls_frame.grid_rowconfigure(0, minsize=24)

        self.opacity_label = tk.Label(
            self.controls_frame,
            text="Opacity",
            fg=UI_COLORS["text"],
            bg=UI_COLORS["outer_bg"],
            font=("Segoe UI", 9),
        )
        self.opacity_label.grid(
            row=0,
            column=0,
            padx=(0, 8),
            pady=0,
            sticky="nsw",
        )

        self.opacity_scale = tk.Scale(
            self.controls_frame,
            from_=MIN_OPACITY,
            to=MAX_OPACITY,
            resolution=0.01,
            orient="horizontal",
            variable=self.opacity_var,
            bg=UI_COLORS["outer_bg"],
            fg=UI_COLORS["text"],
            highlightthickness=0,
            troughcolor=UI_COLORS["scale_trough"],
            command=self._on_opacity_change,
            length=180,
            showvalue=0,
        )
        self.opacity_scale.grid(
            row=0,
            column=1,
            padx=0,
            pady=0,
            sticky="ew",
        )

        self.toggle_button = tk.Button(
            self.controls_frame,
            text=self._collapse_symbol(),
            width=2,
            bg=UI_COLORS["button_bg"],
            fg="white",
            activebackground=UI_COLORS["button_active_bg"],
            relief="flat",
            command=self._toggle_collapse,
        )
        self.toggle_button.grid(
            row=0,
            column=2,
            padx=(12, 0),
            pady=0,
            sticky="nse",
        )

        self.shortcut_container = tk.Frame(
            self.content_frame,
            bg=UI_COLORS["outer_bg"],
        )
        self.shortcut_container.pack(fill="both", expand=True)

        self.shortcut_canvas = tk.Canvas(
            self.shortcut_container,
            bg=UI_COLORS["outer_bg"],
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = tk.Scrollbar(
            self.shortcut_container,
            orient="vertical",
            command=self.shortcut_canvas.yview,
        )
        self.shortcut_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.shortcut_canvas.pack(side="left", fill="both", expand=True)

        self.shortcut_inner_frame = tk.Frame(
            self.shortcut_canvas,
            bg=UI_COLORS["outer_bg"],
        )
        self.shortcut_window_id = self.shortcut_canvas.create_window(
            (0, 0),
            window=self.shortcut_inner_frame,
            anchor="nw",
        )

        self.shortcut_inner_frame.bind(
            "<Configure>",
            self._on_shortcuts_frame_configure,
        )
        self.shortcut_canvas.bind("<Configure>", self._on_canvas_configure)
        self.shortcut_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.shortcut_inner_frame.bind("<MouseWheel>", self._on_mousewheel)

    def _build_context_menu(self) -> None:
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Reload Shortcuts", command=self._reload_config)
        menu.add_command(
            label="Edit JSON",
            command=self._open_config_in_editor,
        )
        menu.add_separator()
        menu.add_command(
            label="Expand/Collapse",
            command=self._toggle_collapse,
        )
        menu.add_command(label="Minimize", command=self._minimize_window)
        menu.add_command(label="Restore", command=self._restore_window)
        menu.add_separator()
        menu.add_command(label="Close", command=self.root.destroy)
        self.context_menu = menu

    def _collapse_symbol(self) -> str:
        return "+" if self.is_collapsed else "-"

    def _show_context_menu(self, event: tk.Event) -> None:
        if self.context_menu is None:
            return
        self.context_menu.tk_popup(event.x_root, event.y_root)
        self.context_menu.grab_release()

    def _on_mousewheel(self, event: tk.Event) -> None:
        if self.is_collapsed or self.shortcut_canvas is None:
            return
        delta = int(-1 * (event.delta / 120))
        if delta != 0:
            self.shortcut_canvas.yview_scroll(delta, "units")

    def _on_shortcuts_frame_configure(self, _: tk.Event) -> None:
        if self.shortcut_canvas is None:
            return
        self.shortcut_canvas.configure(
            scrollregion=self.shortcut_canvas.bbox("all"),
        )

    def _on_canvas_configure(self, event: tk.Event) -> None:
        if self.shortcut_canvas is None or self.shortcut_window_id is None:
            return
        self.shortcut_canvas.itemconfigure(
            self.shortcut_window_id,
            width=event.width,
        )

    def _render_shortcuts(self) -> None:
        if self.shortcut_inner_frame is None:
            return

        for child in self.shortcut_inner_frame.winfo_children():
            child.destroy()

        shortcuts = self.config.get("shortcuts", [])
        if not shortcuts:
            tk.Label(
                self.shortcut_inner_frame,
                text="No shortcuts yet.\nRight-click to edit JSON.",
                justify="center",
                fg=UI_COLORS["text"],
                bg=UI_COLORS["outer_bg"],
                font=("Segoe UI", 10),
            ).pack(fill="both", expand=True, pady=20)
            return

        for item in shortcuts:
            label = item["label"]
            target = item["target"]
            button = tk.Button(
                self.shortcut_inner_frame,
                text=label,
                anchor="w",
                padx=10,
                bg=UI_COLORS["button_bg"],
                fg="white",
                activebackground=UI_COLORS["button_active_bg"],
                relief="flat",
                command=lambda selected=target: open_target(selected),
            )
            button.pack(fill="x", pady=4)

    def _toggle_collapse(self) -> None:
        if self.is_collapsed:
            self._expand_shortcuts()
        else:
            self._collapse_shortcuts()

    def _apply_collapsed_layout(self) -> None:
        if self.shortcut_container is None:
            return

        if self.is_collapsed:
            self.shortcut_container.pack_forget()
            if self.opacity_label is not None:
                self.opacity_label.grid_remove()
            if self.content_frame is not None:
                self.content_frame.pack_configure(pady=4)
            if self.opacity_row is not None:
                self.opacity_row.pack_configure(pady=0)
            self.root.minsize(MIN_WIDTH, COLLAPSED_HEIGHT)
            self.root.resizable(True, False)
            current = parse_geometry(self.root.geometry())
            if current is not None:
                width, _, x, y = current
                collapsed_geometry = build_geometry(
                    max(MIN_WIDTH, width),
                    COLLAPSED_HEIGHT,
                    x,
                    y,
                )
                if collapsed_geometry != self.root.geometry():
                    self.root.geometry(collapsed_geometry)
        else:
            if (
                self.opacity_label is not None
                and not self.opacity_label.winfo_ismapped()
            ):
                self.opacity_label.grid()
            if not self.shortcut_container.winfo_ismapped():
                self.shortcut_container.pack(fill="both", expand=True)
            if self.content_frame is not None:
                self.content_frame.pack_configure(pady=10)
            if self.opacity_row is not None:
                self.opacity_row.pack_configure(pady=(0, 10))
            self.root.minsize(MIN_WIDTH, MIN_EXPANDED_HEIGHT)
            self.root.resizable(True, True)

        if self.toggle_button is not None:
            self.toggle_button.configure(text=self._collapse_symbol())

    def _collapse_shortcuts(self) -> None:
        if self.is_collapsed:
            return

        self.config["expanded_geometry"] = self.root.geometry()
        self.is_collapsed = True
        self.config["is_collapsed"] = True
        self._apply_collapsed_layout()

        self.root.update_idletasks()
        width = self.root.winfo_width()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        collapsed_geometry = build_geometry(width, COLLAPSED_HEIGHT, x, y)
        self.root.geometry(collapsed_geometry)
        self.config["collapsed_geometry"] = collapsed_geometry
        self.config["geometry"] = collapsed_geometry
        self._schedule_save()

    def _expand_shortcuts(self) -> None:
        if not self.is_collapsed:
            return

        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        expanded = self.config.get("expanded_geometry", DEFAULT_GEOMETRY)
        parsed = parse_geometry(expanded)
        if parsed is None:
            target_width = self.root.winfo_width()
            target_height = 420
        else:
            target_width, target_height, _, _ = parsed

        expanded_geometry = build_geometry(
            max(MIN_WIDTH, target_width),
            max(MIN_EXPANDED_HEIGHT, target_height),
            current_x,
            current_y,
        )
        self.root.geometry(expanded_geometry)

        self.is_collapsed = False
        self.config["is_collapsed"] = False
        self.config["expanded_geometry"] = expanded_geometry
        self.config["geometry"] = expanded_geometry
        self._apply_collapsed_layout()
        self._schedule_save()

    def _schedule_save(self) -> None:
        if self._save_after_id is not None:
            self.root.after_cancel(self._save_after_id)
        self._save_after_id = self.root.after(250, self._save_config_now)

    def _current_save_state(self) -> tuple[str, float, bool]:
        """Return normalized state used to decide whether save is needed."""
        return (
            self.root.geometry(),
            round(float(self.opacity_var.get()), 3),
            self.is_collapsed,
        )

    def _save_config_now(self) -> None:
        self._save_after_id = None
        state = self._current_save_state()
        if state == self._last_saved_state:
            return

        current_geometry = self.root.geometry()
        self.config["geometry"] = current_geometry
        self.config["opacity"] = clamp(
            float(self.opacity_var.get()),
            MIN_OPACITY,
            MAX_OPACITY,
        )
        self.config["is_collapsed"] = self.is_collapsed

        if self.is_collapsed:
            self.config["collapsed_geometry"] = current_geometry
        else:
            self.config["expanded_geometry"] = current_geometry

        save_config(self.config)
        self._last_saved_state = state

    def _on_opacity_change(self, _: str) -> None:
        new_opacity = clamp(
            float(self.opacity_var.get()),
            MIN_OPACITY,
            MAX_OPACITY,
        )
        self.root.attributes("-alpha", new_opacity)
        self.config["opacity"] = new_opacity
        self._schedule_save()

    def _on_window_configure(self, _: tk.Event) -> None:
        self._schedule_save()

    def _minimize_window(self) -> None:
        self.root.iconify()

    def _restore_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)

    def _open_config_in_editor(self) -> None:
        try:
            os.startfile(CONFIG_PATH)  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror(
                APP_NAME,
                f"Could not open config file:\n{exc}",
            )

    def _reload_config(self) -> None:
        self.config = load_config()
        self.is_collapsed = bool(self.config.get("is_collapsed", False))
        self.root.geometry(self.config.get("geometry", DEFAULT_GEOMETRY))
        self.root.attributes("-alpha", self.config.get("opacity", 0.92))
        self.opacity_var.set(self.config.get("opacity", 0.92))
        self._render_shortcuts()
        self._apply_collapsed_layout()
        self._last_saved_state = self._current_save_state()


def main() -> int:
    """Run FleetKey app."""
    root = tk.Tk()
    FloatingShortcutsApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
