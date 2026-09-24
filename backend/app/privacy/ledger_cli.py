"""Explicit bootstrap command for the production privacy deletion ledger."""

from __future__ import annotations

import argparse

from app.privacy.tombstones import (
    initialize_ledger,
    upgrade_legacy_ledger,
    validate_ledger,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the privacy deletion ledger")
    parser.add_argument("action", choices=("init", "upgrade", "verify"))
    args = parser.parse_args()
    if args.action == "init":
        path = initialize_ledger()
        print(f"initialized privacy deletion ledger: {path}")
    elif args.action == "upgrade":
        path = upgrade_legacy_ledger()
        print(f"upgraded privacy deletion ledger: {path}")
    else:
        validate_ledger()
        print("privacy deletion ledger verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
