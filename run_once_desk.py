"""One-shot CLI recommendation + optional desktop alert.

Usage:
  python run_once.py
  python run_once.py --stop 75 --alert
  python run_once.py --watch 60
"""

from __future__ import annotations

import argparse
import time

from alerts import RecommendationTracker
from analyzer import analyze_all
from config import HARD_STOP_DEFAULT_USD, PROTOCOL_NAME, PROTOCOL_SHORT, RULEBOOK_VERSION


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"{PROTOCOL_NAME} (v{RULEBOOK_VERSION}) — session micro selector"
    )
    parser.add_argument("--stop", type=float, default=HARD_STOP_DEFAULT_USD, help="Hard dollar stop (50–100)")
    parser.add_argument("--alert", action="store_true", help="Fire desktop notification")
    parser.add_argument("--watch", type=int, default=0, metavar="SEC", help="Re-run every N seconds")
    args = parser.parse_args()

    tracker = RecommendationTracker()

    def run() -> None:
        rec = analyze_all(hard_stop_usd=args.stop)
        print("=" * 64)
        print(f"{PROTOCOL_SHORT} Rulebook v{RULEBOOK_VERSION}")
        print(rec.alert_message)
        print(rec.summary)
        print(f"As of: {rec.as_of} | Phase: {rec.session_phase}")
        print(f"Chart pair: {rec.chart_pair_global}")
        print(f"Static HTF: {rec.static_htf_global}")
        print("-" * 64)
        for s in sorted(rec.scores, key=lambda x: -x.score):
            flag = " <== PICK" if rec.recommended == s.short and not rec.sit_out else ""
            print(
                f"  {s.short:4}  score={s.score:5.1f}  "
                f"struct=${s.range_width_usd:6.0f}  "
                f"pos={s.position_in_range:4.0%}  "
                f"{'BOUNDARY' if s.at_extreme else 'mid     '}  "
                f"1H={s.htf_bias:8}  "
                f"{s.grade}{flag}"
            )
            for r in s.reasons[:3]:
                print(f"         + {r}")
            for w in s.warnings[:2]:
                print(f"         ! {w}")
        print("=" * 64)
        if args.alert or args.watch:
            tracker.maybe_alert(rec.recommended, rec.sit_out, rec.alert_message)

    if args.watch > 0:
        print(f"Watching every {args.watch}s… Ctrl+C to stop.")
        while True:
            run()
            time.sleep(args.watch)
    else:
        run()


if __name__ == "__main__":
    main()
