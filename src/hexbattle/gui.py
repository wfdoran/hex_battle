"""Tkinter user interface.

A start screen picks human vs computer (with the computer's level) or human
vs human.  Human vs human is played "hot seat" on one screen: between turns a
hand-off screen hides the board, and each player has their own log so
neither learns what the other's fog of war hides.
"""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Iterable
from tkinter import messagebox

from . import icons
from .ai import LEVELS, ComputerPlayer
from .combat import battle_odds
from .game import (ANCHOR_BONUS, DRAW, IDLE_TURNS_FOR_DRAW, MIN_DEFENSE, MIN_MOVEMENT, QUIET_TURNS_FOR_FATIGUE,
                   QUIET_TURNS_FOR_RADIATION, FatigueEvent, Game, MoveResult, Phase,
                   RadiationEvent, RangedResult, opponent)
from .grid import ALL_HEXES, COLUMN_LETTERS, Hex, label
from .units import Unit

HUMAN, COMPUTER = 1, 2  # sides in a human vs computer game
HUMAN_VS_COMPUTER, HUMAN_VS_HUMAN = "hvc", "hvh"
PLAYER_NAMES = {1: "Blue", 2: "Red"}
SQRT3 = math.sqrt(3)

COLORS = {
    "board_bg": "#2e3238",
    "hex_visible": "#e8dec3",
    "hex_fog": "#8d8f92",
    "hex_outline": "#5b5850",
    "hex_void": "#25282c",
    "hex_void_outline": "#34383d",
    "hot_visible": "#e3e36a",
    "hot_fog": "#a6a764",
    "trefoil": "#3b3a16",
    "label_visible": "#8a7f66",
    "label_fog": "#6c6e70",
    "move": "#a9d89b",
    "attack": "#f1a196",
    "target": "#d7301f",
    "selected": "#ffcf33",
    "flash": "#ff8a00",
    "tile_outline": "#1c1c1c",
    "tile_text": "#ffffff",
    "tired_text": "#ffd84d",  # a stat lowered by fatigue
    "heart": "#ff5c74",
    "legend_icon": "#3a3a3a",
    "splash_text": "#e8dec3",
    "splash_dim": "#9aa0a8",
    "toggle": "#454b54",
    "toggle_active": "#59606b",
    "toggle_selected": "#3a6db5",
    "start": "#3f8f4f",
    "warning": "#c25e00",
    "muted": "#666666",
    "odds_bg": "#fffaf0",
    "odds_outline": "#3a3a3a",
    "odds_text": "#2b2b2b",
}
TILE_COLORS = {1: "#3a6db5", 2: "#b5432f"}
SPENT_TILE_COLORS = {1: "#8ea7cc", 2: "#cc958b"}  # units that cannot act any more this phase

PANEL_WIDTH = 270
ROSTER_TILE = 72
STEP_MS = 130  # animation time per hex moved
FLASH_MS = 700  # how long a battle or hit is highlighted
AI_PAUSE_MS = 150  # pause between computer actions


def unit_name(u: Unit) -> str:
    return f"{PLAYER_NAMES[u.owner]} #{u.kind}"


def attack_text(u: Unit, anchored: bool) -> str:
    """The unit's attack, shown as x+1 while it is anchored."""
    return f"{u.attack}+{ANCHOR_BONUS}" if anchored else str(u.attack)


def describe(u: Unit, rested: dict[str, int] | None = None, anchored: bool = False) -> str:
    """The unit's stats; `rested` holds the values of any that fatigue lowered."""
    rested = rested or {}

    def stat(name: str) -> str:
        value = f"{name} {getattr(u, name)}"
        if name == "attack" and anchored:
            value = f"attack {attack_text(u, anchored)} (anchored: +{ANCHOR_BONUS} when it fires)"
        return value + f" (tired; was {rested[name]})" if name in rested else value

    return (f"{unit_name(u)}: health {u.health}/{u.max_health}, {stat('attack')}, "
            f"{stat('defense')}, {stat('range')}, {stat('movement')}, {stat('sight')}")


def percent(p: float) -> str:
    """A probability as a whole percentage, without rounding a real chance to 0 or 100."""
    if 0 < p < 0.005:
        return "<1%"
    if 0.995 < p < 1:
        return ">99%"
    return f"{p:.0%}"


def column_names(cols: tuple[int, ...]) -> str:
    return " and ".join(COLUMN_LETTERS[c] for c in cols)


def draw_tile(cv: tk.Canvas, cx: float, cy: float, s: float, unit: Unit, health: int,
              fill: str, tired: Iterable[str] = (), anchored: bool = False) -> None:
    """Draw a unit as a square tile of side s: stats on top, hearts below.
    Stats named in `tired`, lowered by fatigue, are drawn in a warning color.
    An anchored unit's attack is shown as x+1."""
    x0, y0 = cx - s / 2, cy - s / 2
    cv.create_rectangle(x0, y0, x0 + s, y0 + s, fill=fill, outline=COLORS["tile_outline"],
                        width=max(1.0, s / 40))
    isz = s * 0.17
    font = ("Helvetica", -max(7, round(s * 0.17)), "bold")
    # Attack and defense on top, with room for an anchored attack's "x+1";
    # range, movement and sight below.
    slots = [(x0 + s * fx, y0 + s * fy) for fx, fy in
             ((0.20, 0.16), (0.70, 0.16), (1 / 6, 0.39), (3 / 6, 0.39), (5 / 6, 0.39))]
    for (stat, draw_icon), (sx, sy) in zip(icons.STAT_ICONS, slots):
        draw_icon(cv, sx - isz * 0.45, sy, isz, COLORS["tile_text"])
        color = COLORS["tired_text" if stat in tired else "tile_text"]
        text = attack_text(unit, anchored) if stat == "attack" else str(getattr(unit, stat))
        cv.create_text(sx + isz * 0.22, sy, text=text, font=font, fill=color, anchor="w")
    rows = [0.72] if unit.max_health <= 4 else [0.62, 0.84]
    for i in range(unit.max_health):
        row, col = divmod(i, 4)
        hx = x0 + s * (0.14 + col * 0.24)
        hy = y0 + s * rows[row]
        filled = i < health
        icons.heart(cv, hx, hy, s * 0.18, COLORS["heart"] if filled else "", COLORS["tile_text"])


class App:
    def __init__(self, root: tk.Tk, seed: int | None = None):
        self.root = root
        root.title("Hex Battle")
        root.minsize(1000, 640)
        root.configure(bg=COLORS["board_bg"])
        self.mode = tk.StringVar(value=HUMAN_VS_COMPUTER)
        self.level = tk.StringVar(value="medium")
        self.seed_text = tk.StringVar(value="" if seed is None else str(seed))
        self.game: Game | None = None
        self.splash = self._build_splash()
        self.main = self._build_main()
        self.show_splash()

    # ----- start screen ------------------------------------------------------

    def _build_splash(self) -> tk.Frame:
        bg = COLORS["board_bg"]
        frame = tk.Frame(self.root, bg=bg)
        inner = tk.Frame(frame, bg=bg)
        inner.place(relx=0.5, rely=0.5, anchor="center")
        banner = tk.Canvas(inner, width=600, height=250, bg=bg, highlightthickness=0)
        banner.pack()
        self._draw_banner(banner)

        toggle = dict(indicatoron=False, bg=COLORS["toggle"], fg="white",
                      selectcolor=COLORS["toggle_selected"],
                      activebackground=COLORS["toggle_active"], activeforeground="white",
                      relief="flat", bd=0, highlightthickness=0, pady=8,
                      font=("Helvetica", 12, "bold"))

        def section(text: str) -> tk.Frame:
            tk.Label(inner, text=text, bg=bg, fg=COLORS["splash_dim"],
                     font=("Helvetica", 10, "bold")).pack(pady=(18, 6))
            row = tk.Frame(inner, bg=bg)
            row.pack()
            return row

        row = section("PLAYERS")
        for value, text in ((HUMAN_VS_COMPUTER, "Human vs Computer"),
                            (HUMAN_VS_HUMAN, "Human vs Human")):
            tk.Radiobutton(row, text=text, variable=self.mode, value=value, width=20,
                           command=self._update_splash, **toggle).pack(side=tk.LEFT, padx=6)

        row = section("COMPUTER LEVEL")
        self.level_buttons = []
        for value in LEVELS:
            b = tk.Radiobutton(row, text=value.capitalize(), variable=self.level, value=value,
                               width=12, **toggle)
            b.pack(side=tk.LEFT, padx=6)
            self.level_buttons.append(b)
        self.level_note = tk.Label(inner, bg=bg, fg=COLORS["splash_dim"], font=("Helvetica", 10))
        self.level_note.pack(pady=(4, 0))

        row = section("SEED")
        entry = tk.Entry(row, textvariable=self.seed_text, width=12, font=("Helvetica", 12),
                         justify="center", relief="flat")
        entry.pack(side=tk.LEFT, padx=6)
        entry.bind("<Return>", lambda e: self.start_from_splash())
        tk.Label(inner, bg=bg, fg=COLORS["splash_dim"], font=("Helvetica", 10),
                 text="Leave blank for new random units, or enter the seed of an "
                      "earlier game to replay its units.").pack(pady=(4, 0))

        tk.Button(inner, text="Start game", command=self.start_from_splash,
                  bg=COLORS["start"], fg="white", activebackground="#4fa45f",
                  activeforeground="white", relief="flat", bd=0, highlightthickness=0,
                  font=("Helvetica", 14, "bold"), padx=30, pady=10).pack(pady=(26, 0))
        return frame

    def _draw_banner(self, cv: tk.Canvas) -> None:
        cv.create_text(300, 48, text="HEX BATTLE", fill=COLORS["splash_text"],
                       font=("Helvetica", 40, "bold"))
        cv.create_text(300, 92, text="A turn-based war game in the fog of war",
                       fill=COLORS["splash_dim"], font=("Helvetica", 12))
        r = 42
        samples = {
            0: Unit(1, 1, 6, 3, 3, 0, 2, 1),
            1: Unit(1, 2, 5, 2, 1, 3, 2, 2),
            3: Unit(2, 3, 5, 2, 1, 3, 2, 2),
            4: Unit(2, 4, 6, 3, 3, 0, 2, 1),
        }
        samples[1].health = 3
        for i in range(5):
            x = 300 + (i - 2) * 1.5 * r
            y = 168 + (0 if i % 2 else r * SQRT3 / 2) - r * SQRT3 / 4
            hot = i == 2
            pts = [c for k in range(6) for c in (x + r * math.cos(math.pi / 3 * k),
                                                  y + r * math.sin(math.pi / 3 * k))]
            cv.create_polygon(pts, fill=COLORS["hot_visible"] if hot else COLORS["hex_visible"],
                              outline=COLORS["hex_outline"])
            if hot:
                icons.radiation(cv, x, y, r * 1.1, COLORS["trefoil"], COLORS["hot_visible"])
            else:
                u = samples[i]
                draw_tile(cv, x, y, r * 1.24, u, u.health, TILE_COLORS[u.owner])

    def _update_splash(self) -> None:
        hvh = self.mode.get() == HUMAN_VS_HUMAN
        for b in self.level_buttons:
            b.config(state=tk.DISABLED if hvh else tk.NORMAL)
        self.level_note.config(text="Two players share this screen; no computer player."
                               if hvh else "You play Blue; the computer plays Red.")

    def show_splash(self) -> None:
        self.main.pack_forget()
        self._update_splash()
        self.splash.pack(fill=tk.BOTH, expand=True)

    def start_from_splash(self) -> None:
        text = self.seed_text.get().strip()
        if text and not text.isdigit():
            messagebox.showerror("Seed", "The seed must be a whole number.", parent=self.root)
            return
        self.seed_text.set("")
        self.splash.pack_forget()
        self.main.pack(fill=tk.BOTH, expand=True)
        self.new_game(int(text) if text else None)

    # ----- main screen layout ------------------------------------------------

    def _build_main(self) -> tk.Frame:
        frame = tk.Frame(self.root)
        self.canvas = tk.Canvas(frame, width=1100, height=720, bg=COLORS["board_bg"],
                                highlightthickness=0)
        side = tk.Frame(frame, padx=10, pady=10)
        side.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def text_label(**kw) -> tk.Label:
            lbl = tk.Label(side, anchor="w", justify="left", wraplength=PANEL_WIDTH, **kw)
            lbl.pack(fill=tk.X)
            return lbl

        self.status = text_label(font=("Helvetica", 14, "bold"))
        self.counts = text_label(font=("Helvetica", 11, "bold"))
        self.radiation_label = text_label(font=("Helvetica", 10))
        self.hint = text_label()
        self.hint.pack_configure(pady=(4, 8))
        self.panel = tk.Canvas(side, width=PANEL_WIDTH, height=4 * (ROSTER_TILE + 10),
                               highlightthickness=0, bg=side.cget("bg"))
        self.panel.pack()
        buttons = tk.Frame(side)
        buttons.pack(fill=tk.X, pady=8)
        self.random_btn = tk.Button(buttons, text="Random placement",
                                    command=self.on_random_placement)
        self.action_btn = tk.Button(buttons, font=("Helvetica", 11, "bold"),
                                    command=self.on_action)
        self.random_btn.pack(side=tk.LEFT)
        self.action_btn.pack(side=tk.RIGHT)
        self.info = text_label(fg="#555555", height=3)
        log_frame = tk.Frame(side)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.log_text = tk.Text(log_frame, width=38, height=10, wrap="word", state="disabled",
                                font=("Helvetica", 10))
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bottom = tk.Frame(side)
        bottom.pack(fill=tk.X, pady=(8, 0))
        self.seed_label = tk.Label(bottom, fg=COLORS["muted"])
        self.seed_label.pack(side=tk.LEFT)
        self.new_btn = tk.Button(bottom, text="New game", command=self.on_new_game)
        self.new_btn.pack(side=tk.RIGHT)

        self.canvas.bind("<Configure>", lambda e: self.draw_board())
        self.canvas.bind("<Button-1>", self.on_board_click)
        self.canvas.bind("<Button-3>", self.on_board_right_click)
        self.canvas.bind("<Motion>", self.on_board_hover)
        self.canvas.bind("<Leave>", self.on_board_leave)
        self.panel.bind("<Button-1>", self.on_panel_click)
        self.panel.bind("<Motion>", self.on_panel_hover)
        return frame

    # ----- game lifecycle --------------------------------------------------

    def new_game(self, seed: int | None) -> None:
        g = self.game = Game(seed=seed)
        self.hot_seat = self.mode.get() == HUMAN_VS_HUMAN
        self.humans = {1, 2} if self.hot_seat else {HUMAN}
        self.ai = None
        if not self.hot_seat:
            self.ai = ComputerPlayer(COMPUTER, self.level.get(), g.rng)
            self.ai.place_units(g)  # done blind, before the human places
        self.viewer = 1  # whose view of the board is shown
        self.handoff: int | None = None  # player the screen is being handed to
        self.selected: Unit | None = g.units_of(self.viewer)[0]
        self.move_targets: dict[Hex, list[Hex]] = {}
        self.ranged_targets: list[Unit] = []
        self.busy = False  # True while animating or while the computer plays
        self.override: dict | None = None  # board view used during animations
        self.flash: Hex | None = None
        self.announced = False
        self.panel_hits: list[tuple[float, float, float, float, Unit]] = []
        self.logs: dict[int, list[str]] = {1: [], 2: []}
        # For the hot-seat loss summary: how each destroyed unit was lost, as
        # its owner would describe it, and each player's units as they last saw them.
        self.losses: dict[Unit, str] = {}
        self.last_seen_alive: dict[int, set[Unit]] = {1: set(), 2: set()}
        self.show_log()
        self.post_all(f"New game, seed {g.seed}.")
        if self.hot_seat:
            self.post_all("Hot seat: Blue places first while Red looks away.")
        else:
            self.post(HUMAN, f"You are Blue against the {self.level.get()} computer. "
                             "Place your 10 units in the three left columns.")
        self.refresh()

    def announce(self) -> None:
        if self.announced:
            return
        self.announced = True
        g = self.game
        if g.winner == DRAW:
            reason = ("both players passed a turn" if g.idle_turns >= IDLE_TURNS_FOR_DRAW
                      else "the last units were destroyed together")
            text = f"The game is a draw ({reason})."
        elif self.hot_seat:
            text = f"{PLAYER_NAMES[g.winner]} wins!"
        else:
            text = "You win!" if g.winner == HUMAN else "The computer wins."
        self.post_all(text)
        self.refresh()
        messagebox.showinfo("Game over", text, parent=self.root)

    def handoff_to(self, player: int) -> None:
        """Hide the board until `player` is at the screen (hot seat only)."""
        self.handoff = player
        self.clear_selection()
        self.show_log()
        self.refresh()

    def finish_handoff(self) -> None:
        self.viewer = self.handoff
        self.handoff = None
        if self.game.phase is Phase.PLACEMENT:
            self.selected = next((u for u in self.game.units_of(self.viewer) if u.pos is None),
                                 None)
        self.show_log()
        self.refresh()
        self.report_losses()

    def report_losses(self) -> None:
        """Tell the player which of their units were lost since their last turn."""
        lost = [u for u in self.last_seen_alive[self.viewer] if not u.alive]
        if not lost:
            return
        lost.sort(key=lambda u: u.kind)
        self.last_seen_alive[self.viewer] -= set(lost)
        count = f"{len(lost)} of your units" if len(lost) > 1 else "one of your units"
        lines = [f"Since your last turn you lost {count}:", ""]
        lines += [f"• {unit_name(u)} {self.losses.get(u, 'was destroyed')}" for u in lost]
        messagebox.showwarning("Units lost", "\n".join(lines), parent=self.root)

    # ----- logs ------------------------------------------------------------

    def post(self, player: int, msg: str) -> None:
        """Add a line to one player's log."""
        self.logs[player].append(msg)
        if player == self.viewer and self.handoff is None:
            self._append_log(msg)

    def post_all(self, msg: str) -> None:
        for p in (1, 2):
            self.post(p, msg)

    def _append_log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def show_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")
        if self.handoff is None:
            for msg in self.logs[self.viewer]:
                self._append_log(msg)

    # ----- buttons ---------------------------------------------------------

    def on_new_game(self) -> None:
        g = self.game
        if (g.phase is not Phase.PLACEMENT and not g.over
                and not messagebox.askyesno("New game", "Abandon the current game?",
                                            parent=self.root)):
            return
        self.show_splash()

    def on_random_placement(self) -> None:
        if self.handoff is not None:
            return
        self.game.auto_place(self.viewer)
        self.selected = None
        self.refresh()

    def on_action(self) -> None:
        g = self.game
        if self.busy or g.over or self.handoff is not None:
            return
        self.clear_selection()
        if g.phase is Phase.PLACEMENT:
            if not g.placement_done(self.viewer):
                return
            if self.hot_seat and self.viewer == 1:
                self.post(1, "Your units are placed. Red places next.")
                self.handoff_to(2)
                return
            g.start()
            self.last_seen_alive = {p: set(g.units_of(p)) for p in (1, 2)}
            self.post_all("Battle begins. Fog of war is now in effect.")
            if self.hot_seat:
                self.post(1, f"--- Turn {g.turn}: Blue's move ---")
                self.handoff_to(1)
                return
            self.post(HUMAN, f"Turn {g.turn}: your move.")
        elif g.phase is Phase.MOVEMENT:
            g.end_movement()
        elif g.phase is Phase.RANGED:
            self.end_turn()
            return
        self.refresh()

    def end_turn(self) -> None:
        g = self.game
        self.last_seen_alive[g.current] = set(g.units_of(g.current))
        self.log_events(g.end_turn())
        if g.over:
            self.refresh()
            self.announce()
        elif g.current in self.humans:
            self.post(g.current, f"--- Turn {g.turn}: {PLAYER_NAMES[g.current]}'s move ---")
            self.handoff_to(g.current)
        else:
            self.busy = True
            self.post(HUMAN, f"Turn {g.turn}: computer's move.")
            self.refresh()
            self.root.after(AI_PAUSE_MS, self.run_ai)

    # ----- board geometry --------------------------------------------------

    def layout(self) -> None:
        w = max(self.canvas.winfo_width(), 200)
        h = max(self.canvas.winfo_height(), 200)
        margin = 12
        r = min((w - 2 * margin) / 17, (h - 2 * margin) / (6 * SQRT3))
        self.R = max(r, 18)
        self.ox = (w - 17 * self.R) / 2 + self.R
        self.oy = (h - 6 * SQRT3 * self.R) / 2

    def center(self, h: Hex) -> tuple[float, float]:
        c, y = h
        return self.ox + 1.5 * self.R * c, self.oy + y * SQRT3 * self.R / 2

    def hex_points(self, h: Hex, scale: float = 1.0) -> list[float]:
        x, y = self.center(h)
        r = self.R * scale
        return [c for i in range(6)
                for c in (x + r * math.cos(math.pi / 3 * i), y + r * math.sin(math.pi / 3 * i))]

    def hex_at(self, px: float, py: float) -> Hex | None:
        best = min(ALL_HEXES, key=lambda h: math.dist((px, py), self.center(h)))
        return best if math.dist((px, py), self.center(best)) <= self.R * 0.9 else None

    # ----- what the viewer sees ----------------------------------------------

    def view_visible(self) -> set[Hex]:
        if self.override:
            return self.override["vis"]
        return self.game.visible_hexes(self.viewer)

    def view_units(self) -> list[tuple[Unit, Hex, int]]:
        """(unit, hex, health) for every unit on the board as currently displayed."""
        if self.override:
            anim, pos = self.override["anim"], self.override["pos"]
            return [(u, pos if u is anim else h, hp) for u, h, hp in self.override["units"]]
        return [(u, u.pos, u.health) for u in self.game.units if u.alive and u.pos]

    def unit_shown_at(self, h: Hex) -> Unit | None:
        if h not in self.view_visible():
            return None
        for u, pos, _ in self.view_units():
            if pos == h:
                return u
        return None

    def my_turn(self) -> bool:
        """Whether the person at the screen may act right now."""
        g = self.game
        return (g.current in self.humans and g.current == self.viewer
                and self.handoff is None and not self.busy and not g.over)

    def tile_color(self, u: Unit) -> str:
        g = self.game
        spent = False
        if u.owner == g.current and self.my_turn():
            if g.phase is Phase.MOVEMENT:
                spent = u.moved
            elif g.phase is Phase.RANGED:
                spent = u.range == 0 or u.fired or not g.ranged_targets(u)
        return (SPENT_TILE_COLORS if spent else TILE_COLORS)[u.owner]

    # ----- drawing ---------------------------------------------------------

    def refresh(self) -> None:
        g = self.game
        you = PLAYER_NAMES[self.viewer]
        n1, n2 = len(g.units_of(1)), len(g.units_of(2))
        self.counts.config(text=f"Blue: {n1} unit{'s' * (n1 != 1)}     "
                                f"Red: {n2} unit{'s' * (n2 != 1)}")
        if g.radioactive_cols:
            turns = g.radiation_countdown
            self.radiation_label.config(
                fg=COLORS["warning"],
                text=f"☢ Columns {column_names(g.radioactive_cols)} are radioactive! "
                     f"Destroyed after {turns} more turn{'s' * (turns != 1)}.")
        elif g.phase in (Phase.MOVEMENT, Phase.RANGED):
            q = g.quiet_turns
            if q < QUIET_TURNS_FOR_FATIGUE:
                nxt = f"fatigue at {QUIET_TURNS_FOR_FATIGUE}"
            else:
                nxt = f"radiation at {QUIET_TURNS_FOR_RADIATION}"
            self.radiation_label.config(fg=COLORS["muted"],
                                        text=f"Turns without damage: {q} ({nxt})")
        else:
            self.radiation_label.config(text="")
        if g.fatigue and g.phase is not Phase.OVER:
            self.radiation_label.config(
                text=self.radiation_label.cget("text")
                + f"\nFatigue has lowered defense and movement by {g.fatigue}.")
        self.seed_label.config(text=f"Seed: {g.seed}")

        if g.phase is Phase.PLACEMENT:
            self.random_btn.pack(side=tk.LEFT)
        else:
            self.random_btn.pack_forget()
        enabled = False
        if self.handoff is not None:
            name = PLAYER_NAMES[self.handoff]
            status = f"{name}'s turn"
            hint = (f"Hand the screen to {name}. {PLAYER_NAMES[opponent(self.handoff)]}, "
                    f"please look away. {name}: click the board when ready.")
            action = "Waiting"
            self.random_btn.pack_forget()
        elif g.phase is Phase.PLACEMENT:
            placed = sum(1 for u in g.units_of(self.viewer) if u.pos is not None)
            status = f"Setup: {you}" if self.hot_seat else "Setup"
            side = "left" if self.viewer == 1 else "right"
            hint = (f"{placed} of 10 units placed. Click a unit on the right, then a hex in "
                    f"the three {side} columns. Click a placed unit to move it; right-click "
                    "it to take it back. Your opponent cannot see your setup.")
            action = "Done placing" if self.hot_seat and self.viewer == 1 else "Start battle"
            enabled = placed == len(g.units_of(self.viewer))
        elif g.over:
            if g.winner == DRAW:
                status = "Draw."
            elif self.hot_seat:
                status = f"{PLAYER_NAMES[g.winner]} wins!"
            else:
                status = "You win!" if g.winner == HUMAN else "The computer wins."
            hint = "All units are now revealed. Click New game to play again."
            action = "Game over"
        elif g.current not in self.humans:
            status = f"Turn {g.turn}: computer's move"
            hint = "Watch the log for battles and attacks on your units."
            action = "End turn"
        elif g.phase is Phase.MOVEMENT:
            status = (f"Turn {g.turn}: {you} moves" if self.hot_seat
                      else f"Turn {g.turn}: your movement")
            hint = ("Click a unit, then a green hex to move or a red hex to attack. "
                    "Each unit moves once. Click End movement when done.")
            action, enabled = "End movement", True
        else:
            ready = sum(1 for u in g.units_of(g.current) if g.ranged_targets(u))
            status = (f"Turn {g.turn}: {you} fires" if self.hot_seat
                      else f"Turn {g.turn}: ranged attacks")
            hint = (f"{ready} unit(s) can fire. Click a unit, then a target outlined in "
                    "red. There is no counter-attack. Click End turn when done."
                    if ready else "No unit has a target in range. Click End turn.")
            action, enabled = "End turn", True
        self.status.config(text=status)
        self.hint.config(text=hint)
        self.action_btn.config(text=action,
                               state=tk.NORMAL if enabled and not self.busy else tk.DISABLED)
        self.new_btn.config(state=tk.DISABLED if self.busy else tk.NORMAL)
        self.draw_panel()
        self.draw_board()

    def draw_board(self) -> None:
        cv = self.canvas
        cv.delete("all")
        if self.game is None:
            return
        self.layout()
        if self.handoff is not None:
            self.draw_handoff()
            return
        R = self.R
        g = self.game
        vis = self.view_visible()
        targets = {} if self.override else self.move_targets
        label_font = ("Helvetica", -max(8, round(R * 0.16)))
        for h in ALL_HEXES:
            x, y = self.center(h)
            if not g.on_board(h):
                cv.create_polygon(self.hex_points(h), fill=COLORS["hex_void"],
                                  outline=COLORS["hex_void_outline"])
                continue
            hot = h[0] in g.radioactive_cols
            if h in targets:
                fill = COLORS["attack"] if g.unit_at(h) else COLORS["move"]
            elif hot:
                fill = COLORS["hot_visible"] if h in vis else COLORS["hot_fog"]
            else:
                fill = COLORS["hex_visible"] if h in vis else COLORS["hex_fog"]
            cv.create_polygon(self.hex_points(h), fill=fill, outline=COLORS["hex_outline"])
            if hot:
                icons.radiation(cv, x, y, R * 1.1, COLORS["trefoil"], fill)
            cv.create_text(x, y - R * 0.745, text=label(h), font=label_font,
                           fill=COLORS["label_visible"] if h in vis else COLORS["label_fog"])
        for u, pos, hp in self.view_units():
            if pos not in vis:
                continue
            x, y = self.center(pos)
            draw_tile(cv, x, y, R * 1.24, u, hp, self.tile_color(u), g.rested.get(u, ()),
                      g.anchored(u))
            cv.create_text(x, y + R * 0.745, text=f"#{u.kind}", font=label_font,
                           fill=COLORS["label_visible"])
        if self.selected is not None and self.selected.pos and not self.override:
            cv.create_polygon(self.hex_points(self.selected.pos, 0.94), fill="",
                              outline=COLORS["selected"], width=4)
        for t in self.ranged_targets:
            cv.create_polygon(self.hex_points(t.pos, 0.94), fill="", outline=COLORS["target"],
                              width=4)
        if self.flash is not None:
            cv.create_polygon(self.hex_points(self.flash, 0.94), fill="",
                              outline=COLORS["flash"], width=7)

    def draw_handoff(self) -> None:
        cv = self.canvas
        w, h = cv.winfo_width(), cv.winfo_height()
        name = PLAYER_NAMES[self.handoff]
        other = PLAYER_NAMES[opponent(self.handoff)]
        cv.create_text(w / 2, h / 2 - 50, text=f"{name}'s turn", fill=TILE_COLORS[self.handoff],
                       font=("Helvetica", 40, "bold"))
        cv.create_text(w / 2, h / 2 + 20, fill=COLORS["splash_text"], justify="center",
                       font=("Helvetica", 15),
                       text=f"{other}, please look away.\n{name}, click anywhere when ready.")

    def draw_panel(self) -> None:
        p = self.panel
        p.delete("all")
        self.panel_hits = []
        if self.handoff is not None:
            return
        if self.game.phase is Phase.PLACEMENT:
            unplaced = [u for u in self.game.units_of(self.viewer) if u.pos is None]
            if not unplaced:
                p.create_text(PANEL_WIDTH / 2, 40, width=PANEL_WIDTH - 20,
                              text="All units placed.", font=("Helvetica", 12),
                              justify="center")
            step = ROSTER_TILE + 12
            for i, u in enumerate(unplaced):
                row, col = divmod(i, 3)
                cx = step / 2 + col * step
                cy = step / 2 + row * (ROSTER_TILE + 8)
                if u is self.selected:
                    p.create_rectangle(cx - step / 2 + 1, cy - step / 2 + 3,
                                       cx + step / 2 - 1, cy + step / 2 - 3,
                                       fill=COLORS["selected"], outline="")
                draw_tile(p, cx, cy, ROSTER_TILE, u, u.health, TILE_COLORS[self.viewer])
                h = ROSTER_TILE / 2
                self.panel_hits.append((cx - h, cy - h, cx + h, cy + h, u))
            return
        rows = [
            (lambda x, y: icons.heart(p, x, y, 18, COLORS["heart"], COLORS["legend_icon"]),
             "Health left (hearts)"),
            *[(lambda x, y, f=f: f(p, x, y, 20, COLORS["legend_icon"]), name.capitalize())
              for name, f in icons.STAT_ICONS],
            (lambda x, y: self._swatch(x, y, COLORS["move"]), "Hex the unit can move to"),
            (lambda x, y: self._swatch(x, y, COLORS["attack"]), "Enemy it can attack (battle)"),
            (lambda x, y: self._swatch(x, y, "", COLORS["target"]), "Ranged target"),
            (lambda x, y: self._swatch(x, y, COLORS["hex_fog"]), "Fog of war"),
            (lambda x, y: (self._swatch(x, y, COLORS["hot_visible"]),
                           icons.radiation(p, x, y, 16, COLORS["trefoil"], COLORS["hot_visible"])),
             "Radioactive: soon destroyed"),
        ]
        for i, (draw, text) in enumerate(rows):
            y = 14 + i * 27
            draw(20, y)
            p.create_text(44, y, text=text, anchor="w", font=("Helvetica", 11))

    def _swatch(self, x: float, y: float, fill: str, outline: str = "#5b5850") -> None:
        self.panel.create_rectangle(x - 10, y - 10, x + 10, y + 10, fill=fill, outline=outline,
                                    width=3 if fill == "" else 1)

    # ----- input -----------------------------------------------------------

    def clear_selection(self) -> None:
        self.selected = None
        self.move_targets = {}
        self.ranged_targets = []

    def on_board_click(self, event) -> None:
        g = self.game
        if self.handoff is not None:
            self.finish_handoff()
            return
        if self.busy or g.over:
            return
        h = self.hex_at(event.x, event.y)
        if g.phase is Phase.PLACEMENT:
            self.click_placement(h)
        elif not self.my_turn():
            return
        elif g.phase is Phase.MOVEMENT:
            self.click_movement(h)
        else:
            self.click_ranged(h)

    def click_placement(self, h: Hex | None) -> None:
        g = self.game
        unit = g.unit_at(h) if h else None
        if unit is not None and unit.owner == self.viewer:
            self.selected = None if unit is self.selected else unit
        elif h is not None and self.selected is not None and g.can_place(self.selected, h):
            from_roster = self.selected.pos is None
            g.place(self.selected, h)
            unplaced = [u for u in g.units_of(self.viewer) if u.pos is None]
            self.selected = unplaced[0] if from_roster and unplaced else None
        else:
            self.selected = None
        self.refresh()

    def on_board_right_click(self, event) -> None:
        g = self.game
        if g.phase is not Phase.PLACEMENT or self.handoff is not None:
            return
        h = self.hex_at(event.x, event.y)
        unit = g.unit_at(h) if h else None
        if unit is not None and unit.owner == self.viewer:
            g.unplace(unit)
            self.selected = unit
            self.refresh()

    def click_movement(self, h: Hex | None) -> None:
        g = self.game
        if self.selected is not None and h in self.move_targets:
            unit = self.selected
            self.clear_selection()
            self.do_move(unit, h, self.human_done)
            return
        unit = g.unit_at(h) if h else None
        if (unit is not None and unit.owner == g.current and not unit.moved
                and unit is not self.selected):
            self.selected = unit
            self.move_targets = g.legal_moves(unit)
        else:
            self.clear_selection()
        self.refresh()

    def click_ranged(self, h: Hex | None) -> None:
        g = self.game
        unit = g.unit_at(h) if h else None
        if self.selected is not None and unit is not None and unit in self.ranged_targets:
            attacker = self.selected
            self.clear_selection()
            result = g.ranged_attack(attacker, unit)
            self.log_ranged(result)
            self.busy = True
            self.after_event(result.hex, self.human_done)
            return
        if unit is not None and unit.owner == g.current and unit is not self.selected:
            targets = g.ranged_targets(unit)
            self.clear_selection()
            if targets:
                self.selected = unit
                self.ranged_targets = targets
        else:
            self.clear_selection()
        self.refresh()

    def on_board_hover(self, event) -> None:
        self.canvas.delete("odds")
        h = self.hex_at(event.x, event.y)
        if h is None or self.handoff is not None or not self.game.on_board(h):
            self.info.config(text="")
            return
        text = label(h) + ("" if h in self.view_visible() else " (fog of war)")
        if h[0] in self.game.radioactive_cols:
            text += " ☢ radioactive"
        unit = self.unit_shown_at(h)
        if unit is not None:
            text += "\n" + describe(unit, self.game.rested.get(unit), self.game.anchored(unit))
            self.show_odds(unit, h, event.x, event.y)
        self.info.config(text=text)

    def on_board_leave(self, event) -> None:
        self.canvas.delete("odds")
        self.info.config(text="")

    def show_odds(self, enemy: Unit, h: Hex, px: float, py: float) -> None:
        """Pop up the battle odds if the selected unit were to attack this enemy."""
        u = self.selected
        g = self.game
        if (u is None or g.phase is not Phase.MOVEMENT or not self.my_turn()
                or u.owner != g.current or enemy.owner == u.owner or h not in self.view_visible()):
            return
        win, lose, both = battle_odds(u.health, u.attack, u.defense,
                                      enemy.health, enemy.attack, enemy.defense)
        rows = [(f"{unit_name(u)} wins", win, TILE_COLORS[u.owner]),
                (f"{unit_name(enemy)} wins", lose, TILE_COLORS[enemy.owner]),
                ("Both destroyed", both, COLORS["odds_text"])]
        note = "" if h in self.move_targets else "Out of reach this move"
        cv = self.canvas
        font = ("Helvetica", -13)
        bold = ("Helvetica", -13, "bold")
        line, pad, width = 19, 9, 200
        height = pad * 2 + line * (len(rows) + 1 + bool(note))
        # Keep the box inside the board, beside the pointer.
        x = px + 18 if px + 18 + width < cv.winfo_width() else px - 18 - width
        y = min(max(4, py - height / 2), cv.winfo_height() - height - 4)
        cv.create_rectangle(x, y, x + width, y + height, fill=COLORS["odds_bg"],
                            outline=COLORS["odds_outline"], tags="odds")
        ty = y + pad + line / 2
        cv.create_text(x + pad, ty, text="Battle odds", anchor="w", font=bold,
                       fill=COLORS["odds_text"], tags="odds")
        for name, p, color in rows:
            ty += line
            cv.create_text(x + pad, ty, text=name, anchor="w", font=font, fill=color, tags="odds")
            cv.create_text(x + width - pad, ty, text=percent(p), anchor="e", font=bold,
                           fill=color, tags="odds")
        if note:
            cv.create_text(x + pad, ty + line, text=note, anchor="w", font=font,
                           fill=COLORS["muted"], tags="odds")

    def _panel_unit(self, event) -> Unit | None:
        for x0, y0, x1, y1, u in self.panel_hits:
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                return u
        return None

    def on_panel_click(self, event) -> None:
        unit = self._panel_unit(event)
        if unit is not None:
            self.selected = unit
            self.refresh()

    def on_panel_hover(self, event) -> None:
        unit = self._panel_unit(event)
        self.info.config(text=describe(unit, self.game.rested.get(unit), self.game.anchored(unit))
                         if unit else "")

    # ----- actions and animation ---------------------------------------------

    def human_done(self) -> None:
        self.busy = False
        self.refresh()
        if self.game.over:
            self.announce()

    def do_move(self, unit: Unit, dest: Hex, then) -> None:
        """Make the move, animate it as the viewer would see it, then call `then`."""
        g = self.game
        before_units = self.view_units()
        before_vis = {p: set(g.visible_hexes(p)) for p in (1, 2)}
        start = unit.pos
        result = g.move(unit, dest)
        walk = [start] + [h for h in result.path
                          if not (result.battle and h == result.battle.hex)]
        shown = before_vis[self.viewer]
        self.busy = True
        self.override = {"units": before_units, "vis": shown, "anim": unit, "pos": start}

        def step(i: int) -> None:
            if i < len(walk):
                self.override["pos"] = walk[i]
                self.draw_board()
                self.root.after(STEP_MS if walk[i] in shown else 0, step, i + 1)
            else:
                self.override = None
                self.log_move(result, before_vis)
                self.after_event(result.battle.hex if result.battle else None, then)

        step(0)

    def after_event(self, h: Hex | None, then) -> None:
        """Briefly highlight hex h (if any), then call `then`."""
        if h is None:
            self.refresh()
            then()
            return
        self.flash = h
        self.refresh()

        def done() -> None:
            self.flash = None
            self.refresh()
            then()

        self.root.after(FLASH_MS, done)

    def run_ai(self) -> None:
        g = self.game
        if g.over:
            self.busy = False
            self.announce()
            return
        action = self.ai.next_action(g)
        if action.kind == "move":
            self.do_move(action.unit, action.target, self.ai_continue)
        elif action.kind == "end_movement":
            g.end_movement()
            self.ai_continue()
        elif action.kind == "ranged":
            result = g.ranged_attack(action.unit, action.target)
            self.log_ranged(result)
            self.after_event(result.hex, self.ai_continue)
        else:
            self.log_events(g.end_turn())
            self.busy = False
            if g.over:
                self.refresh()
                self.announce()
            else:
                self.post(HUMAN, f"Turn {g.turn}: your move.")
                self.refresh()

    def ai_continue(self) -> None:
        self.root.after(AI_PAUSE_MS, self.run_ai)

    # ----- log messages ----------------------------------------------------
    # Each player's log only reports what that player could know.

    def log_move(self, result: MoveResult, before_vis: dict[int, set[Hex]]) -> None:
        u = result.unit
        if result.battle:
            self.log_battle(result)
            return
        end = u.pos
        msg = f"{unit_name(u)} moved {label(result.start)} → {label(end)}."
        if result.stopped_early:
            msg += " An enemy hidden in the fog had it in its zone of control, so it had to stop."
        self.post(u.owner, msg)
        enemy = opponent(u.owner)
        if end in self.game.visible_hexes(enemy):
            origin = label(result.start) if result.start in before_vis[enemy] else "the fog"
            self.post(enemy, f"{unit_name(u)} moved from {origin} to {label(end)}.")

    def log_battle(self, result: MoveResult) -> None:
        b = result.battle
        a, d = b.attacker, b.defender
        rounds = ", ".join(f"{x}-{y}" for x, y in b.rounds)
        self.post_all(f"Battle at {label(b.hex)}: {unit_name(a)} attacked {unit_name(d)}. "
                      f"Damage per round (dealt-taken): {rounds}.")
        where = label(b.hex)
        if not a.alive:
            self.losses[a] = f"was destroyed attacking {unit_name(d)} at {where}."
        if not d.alive:
            self.losses[d] = f"was destroyed at {where}, attacked by {unit_name(a)}."
        if not a.alive and not d.alive:
            self.post_all("  Both units were destroyed.")
        elif a.alive:
            self.post_all(f"  {unit_name(d)} destroyed. {unit_name(a)} takes {label(b.hex)} "
                          f"with {a.health} health.")
        else:
            self.post_all(f"  {unit_name(a)} destroyed. {unit_name(d)} holds {label(b.hex)} "
                          f"with {d.health} health.")

    def log_ranged(self, r: RangedResult) -> None:
        a, t = r.attacker, r.target
        outcome = "destroyed!" if r.killed else f"{t.health} health left."
        for p in (1, 2):
            if a.owner == p or a.pos in self.game.visible_hexes(p):
                shooter = f"{unit_name(a)} at {label(a.pos)}"
                if r.anchored:
                    shooter += f" (anchored, attack {attack_text(a, True)})"
            else:
                shooter = f"A hidden {PLAYER_NAMES[a.owner]} unit"
            self.post(p, f"{shooter} fired at {unit_name(t)} at {label(r.hex)}: "
                         f"{r.damage} damage, {outcome}")
            if r.killed and t.owner == p:
                by = shooter.replace("A hidden", "a hidden")
                self.losses[t] = f"was shot at {label(r.hex)} by {by}."

    def log_events(self, events: list[RadiationEvent | FatigueEvent]) -> None:
        for e in events:
            if isinstance(e, FatigueEvent):
                self.post_all(f"{QUIET_TURNS_FOR_FATIGUE} turns without damage: every unit is "
                              f"fatigued. Defense and movement drop by 1 (to no less than "
                              f"{MIN_DEFENSE} and {MIN_MOVEMENT}).")
                continue
            cols = column_names(e.columns)
            if e.kind == "warning":
                self.post_all(f"☢ {QUIET_TURNS_FOR_RADIATION} turns without damage: "
                              f"columns {cols} are now radioactive! They and any units on "
                              "them will be destroyed in 2 turns.")
                continue
            for u in e.casualties:
                self.losses[u] = f"was destroyed by radiation in columns {cols}."
            for p in (1, 2):
                msg = f"☢ Columns {cols} were destroyed."
                mine = [unit_name(u) for u in e.casualties if u.owner == p]
                theirs = sum(1 for u in e.casualties if u.owner != p)
                if mine:
                    msg += f" Lost: {', '.join(mine)}."
                if theirs:
                    msg += f" {theirs} enemy unit{'s' * (theirs != 1)} destroyed there."
                self.post(p, msg)
