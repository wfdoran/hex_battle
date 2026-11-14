"""Tkinter user interface: the human plays Blue (Player 1) against the computer."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox

from . import icons
from .ai import ComputerPlayer
from .game import DRAW, Game, MoveResult, Phase, RangedResult
from .grid import ALL_HEXES, Hex, label
from .units import Unit

HUMAN, COMPUTER = 1, 2
PLAYER_NAMES = {1: "Blue", 2: "Red"}
SQRT3 = math.sqrt(3)

COLORS = {
    "board_bg": "#2e3238",
    "hex_visible": "#e8dec3",
    "hex_fog": "#8d8f92",
    "hex_outline": "#5b5850",
    "label_visible": "#8a7f66",
    "label_fog": "#6c6e70",
    "move": "#a9d89b",
    "attack": "#f1a196",
    "target": "#d7301f",
    "selected": "#ffcf33",
    "flash": "#ff8a00",
    "tile_outline": "#1c1c1c",
    "tile_text": "#ffffff",
    "heart": "#ff5c74",
    "legend_icon": "#3a3a3a",
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


def describe(u: Unit) -> str:
    return (f"{unit_name(u)}: health {u.health}/{u.max_health}, attack {u.attack}, "
            f"defense {u.defense}, range {u.range}, movement {u.movement}, sight {u.sight}")


def draw_tile(cv: tk.Canvas, cx: float, cy: float, s: float, unit: Unit, health: int,
              fill: str) -> None:
    """Draw a unit as a square tile of side s: stats on top, hearts below."""
    x0, y0 = cx - s / 2, cy - s / 2
    cv.create_rectangle(x0, y0, x0 + s, y0 + s, fill=fill, outline=COLORS["tile_outline"],
                        width=max(1.0, s / 40))
    isz = s * 0.17
    font = ("Helvetica", -max(7, round(s * 0.17)), "bold")
    slots = [(x0 + s * fx, y0 + s * fy) for fx, fy in
             ((1 / 6, 0.16), (3 / 6, 0.16), (5 / 6, 0.16), (0.30, 0.39), (0.70, 0.39))]
    for (stat, draw_icon), (sx, sy) in zip(icons.STAT_ICONS, slots):
        draw_icon(cv, sx - isz * 0.45, sy, isz, COLORS["tile_text"])
        cv.create_text(sx + isz * 0.55, sy, text=str(getattr(unit, stat)), font=font,
                       fill=COLORS["tile_text"])
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
        self.seed = seed
        root.title("Hex Battle")
        root.minsize(980, 620)

        self.canvas = tk.Canvas(root, width=1100, height=720, bg=COLORS["board_bg"],
                                highlightthickness=0)
        side = tk.Frame(root, padx=10, pady=10)
        side.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.status = tk.Label(side, font=("Helvetica", 14, "bold"), anchor="w",
                               justify="left", wraplength=PANEL_WIDTH)
        self.status.pack(fill=tk.X)
        self.hint = tk.Label(side, anchor="w", justify="left", wraplength=PANEL_WIDTH)
        self.hint.pack(fill=tk.X, pady=(4, 8))
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
        self.info = tk.Label(side, anchor="w", justify="left", wraplength=PANEL_WIDTH,
                             fg="#555555", height=3)
        self.info.pack(fill=tk.X)
        log_frame = tk.Frame(side)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.log_text = tk.Text(log_frame, width=38, height=10, wrap="word", state="disabled",
                                font=("Helvetica", 10))
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.new_btn = tk.Button(side, text="New game", command=self.on_new_game)
        self.new_btn.pack(fill=tk.X, pady=(8, 0))

        self.canvas.bind("<Configure>", lambda e: self.draw_board())
        self.canvas.bind("<Button-1>", self.on_board_click)
        self.canvas.bind("<Button-3>", self.on_board_right_click)
        self.canvas.bind("<Motion>", self.on_board_hover)
        self.canvas.bind("<Leave>", lambda e: self.info.config(text=""))
        self.panel.bind("<Button-1>", self.on_panel_click)
        self.panel.bind("<Motion>", self.on_panel_hover)

        self.new_game()

    # ----- game lifecycle --------------------------------------------------

    def new_game(self) -> None:
        self.game = Game(seed=self.seed)
        self.seed = None  # only the first game uses a fixed seed
        self.ai = ComputerPlayer(COMPUTER, self.game.rng)
        self.ai.place_units(self.game)  # done blind, before the human places
        self.selected: Unit | None = self.game.units_of(HUMAN)[0]
        self.move_targets: dict[Hex, list[Hex]] = {}
        self.ranged_targets: list[Unit] = []
        self.busy = False  # True while animating or while the computer plays
        self.override: dict | None = None  # board view used during animations
        self.flash: Hex | None = None
        self.announced = False
        self.panel_hits: list[tuple[float, float, float, float, Unit]] = []
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")
        self.log("New game. Place your 10 units in the three left columns.")
        self.refresh()

    def log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def announce(self) -> None:
        if self.announced:
            return
        self.announced = True
        winner = self.game.winner
        text = {HUMAN: "You win!", COMPUTER: "The computer wins.", DRAW: "The game is a draw."}[winner]
        self.log(text)
        self.refresh()
        messagebox.showinfo("Game over", text, parent=self.root)

    # ----- buttons ---------------------------------------------------------

    def on_new_game(self) -> None:
        if (self.game.phase is not Phase.PLACEMENT and not self.game.over
                and not messagebox.askyesno("New game", "Abandon the current game?",
                                            parent=self.root)):
            return
        self.new_game()

    def on_random_placement(self) -> None:
        self.game.auto_place(HUMAN)
        self.selected = None
        self.refresh()

    def on_action(self) -> None:
        g = self.game
        if self.busy or g.over:
            return
        self.clear_selection()
        if g.phase is Phase.PLACEMENT:
            if g.placement_done(HUMAN):
                g.start()
                self.log("Battle begins. Fog of war is now in effect.")
                self.log(f"Turn {g.turn}: your move.")
        elif g.phase is Phase.MOVEMENT:
            g.end_movement()
        elif g.phase is Phase.RANGED:
            g.end_turn()
            if g.over:
                self.announce()
                return
            self.busy = True
            self.log(f"Turn {g.turn}: computer's move.")
            self.root.after(AI_PAUSE_MS, self.run_ai)
        self.refresh()

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

    # ----- what the human sees ----------------------------------------------

    def view_visible(self) -> set[Hex]:
        if self.override:
            return self.override["vis"]
        return self.game.visible_hexes(HUMAN)

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

    def tile_color(self, u: Unit) -> str:
        g = self.game
        spent = False
        if u.owner == g.current == HUMAN and not self.busy:
            if g.phase is Phase.MOVEMENT:
                spent = u.moved
            elif g.phase is Phase.RANGED:
                spent = u.range == 0 or u.fired or not g.ranged_targets(u)
        return (SPENT_TILE_COLORS if spent else TILE_COLORS)[u.owner]

    # ----- drawing ---------------------------------------------------------

    def refresh(self) -> None:
        g = self.game
        if g.phase is Phase.PLACEMENT:
            placed = sum(1 for u in g.units_of(HUMAN) if u.pos is not None)
            status = "Setup"
            hint = (f"{placed} of 10 units placed. Click a unit on the right, then a hex in "
                    "the three left columns. Click a placed unit to move it; right-click it "
                    "to take it back. The computer is placing its units out of sight.")
            action, enabled = "Start battle", placed == 10
            self.random_btn.pack(side=tk.LEFT)
        else:
            self.random_btn.pack_forget()
            if g.over:
                status = {HUMAN: "You win!", COMPUTER: "The computer wins.",
                          DRAW: "Draw."}[g.winner]
                hint = "All units are now revealed. Click New game to play again."
                action, enabled = "Game over", False
            elif g.current == COMPUTER:
                status = f"Turn {g.turn}: computer's move"
                hint = "Watch the log for battles and attacks on your units."
                action, enabled = "End turn", False
            elif g.phase is Phase.MOVEMENT:
                status = f"Turn {g.turn}: your movement"
                hint = ("Click a unit, then a green hex to move or a red hex to attack. "
                        "Each unit moves once. Click End movement when done.")
                action, enabled = "End movement", True
            else:
                ready = sum(1 for u in g.units_of(HUMAN) if g.ranged_targets(u))
                status = f"Turn {g.turn}: ranged attacks"
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
        self.layout()
        R = self.R
        vis = self.view_visible()
        targets = {} if self.override else self.move_targets
        label_font = ("Helvetica", -max(8, round(R * 0.16)))
        for h in ALL_HEXES:
            x, y = self.center(h)
            if h in targets:
                fill = COLORS["attack"] if self.game.unit_at(h) else COLORS["move"]
            else:
                fill = COLORS["hex_visible"] if h in vis else COLORS["hex_fog"]
            cv.create_polygon(self.hex_points(h), fill=fill, outline=COLORS["hex_outline"])
            cv.create_text(x, y - R * 0.745, text=label(h), font=label_font,
                           fill=COLORS["label_visible"] if h in vis else COLORS["label_fog"])
        for u, pos, hp in self.view_units():
            if pos not in vis:
                continue
            x, y = self.center(pos)
            draw_tile(cv, x, y, R * 1.24, u, hp, self.tile_color(u))
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

    def draw_panel(self) -> None:
        p = self.panel
        p.delete("all")
        self.panel_hits = []
        if self.game.phase is Phase.PLACEMENT:
            unplaced = [u for u in self.game.units_of(HUMAN) if u.pos is None]
            if not unplaced:
                p.create_text(PANEL_WIDTH / 2, 40, width=PANEL_WIDTH - 20,
                              text="All units placed.\nClick Start battle.",
                              font=("Helvetica", 12), justify="center")
            step = ROSTER_TILE + 12
            for i, u in enumerate(unplaced):
                row, col = divmod(i, 3)
                cx = step / 2 + col * step
                cy = step / 2 + row * (ROSTER_TILE + 8)
                if u is self.selected:
                    p.create_rectangle(cx - step / 2 + 1, cy - step / 2 + 3,
                                       cx + step / 2 - 1, cy + step / 2 - 3,
                                       fill=COLORS["selected"], outline="")
                draw_tile(p, cx, cy, ROSTER_TILE, u, u.health, TILE_COLORS[HUMAN])
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
        ]
        for i, (draw, text) in enumerate(rows):
            y = 16 + i * 30
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
        if self.busy or g.over:
            return
        h = self.hex_at(event.x, event.y)
        if g.phase is Phase.PLACEMENT:
            self.click_placement(h)
        elif g.current != HUMAN:
            return
        elif g.phase is Phase.MOVEMENT:
            self.click_movement(h)
        else:
            self.click_ranged(h)

    def click_placement(self, h: Hex | None) -> None:
        g = self.game
        unit = g.unit_at(h) if h else None
        if unit is not None and unit.owner == HUMAN:
            self.selected = None if unit is self.selected else unit
        elif h is not None and self.selected is not None and g.can_place(self.selected, h):
            from_roster = self.selected.pos is None
            g.place(self.selected, h)
            unplaced = [u for u in g.units_of(HUMAN) if u.pos is None]
            self.selected = unplaced[0] if from_roster and unplaced else None
        else:
            self.selected = None
        self.refresh()

    def on_board_right_click(self, event) -> None:
        g = self.game
        if g.phase is not Phase.PLACEMENT:
            return
        h = self.hex_at(event.x, event.y)
        unit = g.unit_at(h) if h else None
        if unit is not None and unit.owner == HUMAN:
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
        if unit is not None and unit.owner == HUMAN and not unit.moved and unit is not self.selected:
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
        if unit is not None and unit.owner == HUMAN and unit is not self.selected:
            targets = g.ranged_targets(unit)
            self.clear_selection()
            if targets:
                self.selected = unit
                self.ranged_targets = targets
        else:
            self.clear_selection()
        self.refresh()

    def on_board_hover(self, event) -> None:
        h = self.hex_at(event.x, event.y)
        if h is None:
            self.info.config(text="")
            return
        text = label(h) + ("" if h in self.view_visible() else " (fog of war)")
        unit = self.unit_shown_at(h)
        if unit is not None:
            text += "\n" + describe(unit)
        self.info.config(text=text)

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
        self.info.config(text=describe(unit) if unit else "")

    # ----- actions and animation ---------------------------------------------

    def human_done(self) -> None:
        self.busy = False
        self.refresh()
        if self.game.over:
            self.announce()

    def do_move(self, unit: Unit, dest: Hex, then) -> None:
        """Make the move, animate it as the human would see it, then call `then`."""
        g = self.game
        before_units = self.view_units()
        before_vis = set(g.visible_hexes(HUMAN))
        start = unit.pos
        result = g.move(unit, dest)
        walk = [start] + [h for h in result.path
                          if not (result.battle and h == result.battle.hex)]
        self.busy = True
        self.override = {"units": before_units, "vis": before_vis, "anim": unit, "pos": start}

        def step(i: int) -> None:
            if i < len(walk):
                self.override["pos"] = walk[i]
                self.draw_board()
                self.root.after(STEP_MS if walk[i] in before_vis else 0, step, i + 1)
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
            g.end_turn()
            self.busy = False
            if g.over:
                self.announce()
            else:
                self.log(f"Turn {g.turn}: your move.")
                self.refresh()

    def ai_continue(self) -> None:
        self.root.after(AI_PAUSE_MS, self.run_ai)

    # ----- log messages ----------------------------------------------------

    def log_move(self, result: MoveResult, before_vis: set[Hex]) -> None:
        u = result.unit
        if result.battle:
            self.log_battle(result)
            return
        end = u.pos
        if u.owner == HUMAN:
            msg = f"{unit_name(u)} moved {label(result.start)} → {label(end)}."
            if result.stopped_early:
                msg += " Enemies hidden in the fog pinned it and it had to stop."
            self.log(msg)
        elif end in self.game.visible_hexes(HUMAN):
            origin = label(result.start) if result.start in before_vis else "the fog"
            self.log(f"{unit_name(u)} moved from {origin} to {label(end)}.")

    def log_battle(self, result: MoveResult) -> None:
        b = result.battle
        a, d = b.attacker, b.defender
        rounds = ", ".join(f"{x}-{y}" for x, y in b.rounds)
        self.log(f"Battle at {label(b.hex)}: {unit_name(a)} attacked {unit_name(d)}. "
                 f"Damage per round (dealt-taken): {rounds}.")
        if not a.alive and not d.alive:
            self.log("  Both units were destroyed.")
        elif a.alive:
            self.log(f"  {unit_name(d)} destroyed. {unit_name(a)} takes {label(b.hex)} "
                     f"with {a.health} health.")
        else:
            self.log(f"  {unit_name(a)} destroyed. {unit_name(d)} holds {label(b.hex)} "
                     f"with {d.health} health.")

    def log_ranged(self, r: RangedResult) -> None:
        a, t = r.attacker, r.target
        if a.owner == HUMAN or a.pos in self.game.visible_hexes(HUMAN):
            shooter = f"{unit_name(a)} at {label(a.pos)}"
        else:
            shooter = f"A hidden {PLAYER_NAMES[a.owner]} unit"
        outcome = "destroyed!" if r.killed else f"{t.health} health left."
        self.log(f"{shooter} fired at {unit_name(t)} at {label(r.hex)}: "
                 f"{r.damage} damage, {outcome}")
