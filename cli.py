"""Command-line interface for the RPGM autoplay system."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the CLI."""

    parser = argparse.ArgumentParser(description="Run the autoplay runner")
    parser.add_argument(
        "--window",
        default="rmmz-game",
        help="Title of the game window to capture",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without sending inputs to the game",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Display per-frame debug information",
    )
    parser.add_argument(
        "--lang",
        default="eng+jpn",
        help="Tesseract language codes (e.g. 'eng+jpn')",
    )
    parser.add_argument(
        "--wall-hand",
        choices=["right", "left"],
        default="right",
        help="Wall-following hand for exploration",
    )
    parser.add_argument(
        "--snapshot-dir",
        default=None,
        help="Directory to save 1 FPS snapshots and perception JSON",
    )
    return parser


def main() -> None:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args()

    from rpgm_autoplay.main_loop import Runner

    runner = Runner(
        window_name=args.window,
        langs=args.lang,
        wall_hand=args.wall_hand,
        debug=args.debug,
        snapshot_dir=args.snapshot_dir,
    )
    runner.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

