"""Entry point: python3 -m hexbattle [--seed N]"""

import argparse
import tkinter as tk
from pathlib import Path

from .gui import App

# The repository's icons folder, next to src/.
ICON_DIR = Path(__file__).resolve().parents[2] / "icons"
ICON_SIZES = (16, 32, 48, 64, 128, 256)


def set_window_icon(root: tk.Tk) -> None:
    """Use the game icon for every window; keep Tk's default if the files are missing."""
    try:
        images = [tk.PhotoImage(master=root, file=ICON_DIR / f"hexbattle-{n}.png") for n in ICON_SIZES]
    except tk.TclError:
        return
    root.iconphoto(True, *images)


def main() -> None:
    parser = argparse.ArgumentParser(prog="hexbattle", description="Play Hex Battle.")
    parser.add_argument("--seed", type=int,
                        help="pre-fill the start screen with this seed to replay its units")
    args = parser.parse_args()
    root = tk.Tk(className="hexbattle")
    set_window_icon(root)
    App(root, seed=args.seed)
    root.mainloop()


if __name__ == "__main__":
    main()
