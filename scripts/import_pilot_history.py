"""Persist real pilot snapshots; optionally backfill dated Git revisions once."""
import argparse
import json
import subprocess

from catalog_db import ROOT, save_pilot_price_history, seed_existing_price_history

PREFIX = "window.NEXO_LIVE_DATA = "


def parse_snapshot(text):
    if not text.startswith(PREFIX):
        raise ValueError("Unexpected live-data.js format")
    snapshot = json.loads(text[len(PREFIX):].strip().removesuffix(";"))
    if not snapshot.get("capturedAt") or not isinstance(snapshot.get("games"), list):
        raise ValueError("Incomplete pilot snapshot")
    return snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill-git", action="store_true", help="import past committed pilot snapshots")
    args = parser.parse_args()
    seed_existing_price_history()
    snapshots = [parse_snapshot((ROOT / "live-data.js").read_text(encoding="utf-8"))]
    if args.backfill_git:
        revisions = subprocess.check_output(
            ["git", "log", "--format=%H", "--", "live-data.js"], cwd=ROOT, text=True
        ).splitlines()
        for revision in revisions:
            text = subprocess.check_output(
                ["git", "show", f"{revision}:live-data.js"], cwd=ROOT, text=True
            )
            snapshots.append(parse_snapshot(text))
    for snapshot in snapshots:
        save_pilot_price_history(snapshot)
    print(f"Imported {len(snapshots)} pilot snapshots into SQLite price history")


if __name__ == "__main__":
    main()
