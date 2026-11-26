"""Scheduler: einmalig (--once) oder taeglich zur konfigurierten Zeit laufen.

Der Container startet mit einem sofortigen Lauf (damit du beim ersten
Start direkt ein Briefing bekommst) und wartet dann auf 04:30 (config.yaml).
"""
import argparse
import datetime
import pathlib
import time
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

load_dotenv()

from briefing.main import run  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent


def seconds_until(cfg_time: str, tz: ZoneInfo) -> float:
    now = datetime.datetime.now(tz)
    hh, mm = (int(x) for x in cfg_time.split(":"))
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()


def main():
    parser = argparse.ArgumentParser(description="Morning Briefing")
    parser.add_argument("--once", action="store_true",
                        help="Einmal laufen und beenden (Test)")
    args = parser.parse_args()

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    tz = ZoneInfo(cfg["run"]["timezone"])
    run_time = cfg["run"]["time"]

    while True:
        try:
            run()
        except Exception as exc:  # noqa: BLE001 - Scheduler darf nie sterben
            print(f"Lauf-Fehler: {exc}")
        if args.once:
            break
        wait = seconds_until(run_time, tz)
        print(f"Nächster Lauf um {run_time} (in {wait / 3600:.1f} h)")
        time.sleep(max(wait, 60))


if __name__ == "__main__":
    main()
