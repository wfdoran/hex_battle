"""Entry point: python3 -m hexbattle [--seed N]"""

import argparse
import tkinter as tk

from .gui import App


def main() -> None:
    parser = argparse.ArgumentParser(prog="hexbattle", description="Play Hex Battle.")
    parser.add_argument("--seed", type=int,
                        help="pre-fill the start screen with this seed to replay its units")
    args = parser.parse_args()
    root = tk.Tk()
    App(root, seed=args.seed)
    root.mainloop()


if __name__ == "__main__":
    main()
