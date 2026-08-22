"""CLI one-shot: print today's CPRP micro pick.

    python run_once.py
    python run_once.py --demo mnq_clear
    python run_once.py --strict
"""

from __future__ import annotations

import argparse
import json

from selector.config import HARD_STOP_DEFAULT_USD, MES_BIAS_POINTS, SWITCH_MARGIN
from selector.history import rec_to_markdown
from selector.providers import load_market_bundle
from selector.scoring import analyze_session


def main() -> None:
    p = argparse.ArgumentParser(description="CPRP Micro Selector — one-shot")
    p.add_argument("--demo", nargs="?", const="mes_default", help="Use bundled sample (mes_default|mnq_clear|sitout)")
    p.add_argument("--json", action="store_true", help="Print JSON instead of markdown")
    p.add_argument("--mild", action="store_true", help="Allow mild momentum days")
    p.add_argument("--stop", type=float, default=HARD_STOP_DEFAULT_USD)
    args = p.parse_args()

    force_mock = args.demo is not None
    scenario = args.demo or "mes_default"
    bundle = load_market_bundle(force_mock=force_mock, scenario=scenario)
    rec = analyze_session(
        bundle,
        mes_bias=MES_BIAS_POINTS,
        switch_margin=SWITCH_MARGIN,
        mode="allow_mild_momentum" if args.mild else "strict_mr",
        hard_stop_usd=args.stop,
    )
    if args.json:
        print(json.dumps(rec.to_dict(), indent=2))
    else:
        print(rec_to_markdown(rec))


if __name__ == "__main__":
    main()
