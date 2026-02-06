#!/usr/bin/env python3
from __future__ import annotations

import os
import sys


def main() -> int:
    pub_cache = os.environ.get("PUB_CACHE") or os.path.join(
        os.path.expanduser("~"), ".pub-cache"
    )
    base_dir = os.path.join(
        pub_cache,
        "hosted",
        "pub.dev",
        "share_plus-12.0.1",
        "android",
        "src",
        "main",
        "kotlin",
        "dev",
        "fluttercommunity",
        "plus",
        "share",
    )
    share_file = os.path.join(base_dir, "Share.kt")
    manager_file = os.path.join(base_dir, "ShareSuccessManager.kt")
    pending_file = os.path.join(base_dir, "SharePlusPendingIntent.kt")

    for path in (share_file, manager_file, pending_file):
        if not os.path.exists(path):
            print(f"share_plus patch: missing file {path}", file=sys.stderr)
            return 1

    with open(share_file, "r", encoding="utf-8") as handle:
        share_content = handle.read()

    package_line = "package dev.fluttercommunity.plus.share"
    if not share_content.lstrip().startswith(package_line):
        updated = f"{package_line}\n\n{share_content.lstrip()}"
        with open(share_file, "w", encoding="utf-8") as handle:
            handle.write(updated)
        print("share_plus patch: package line added to Share.kt")
    else:
        print("share_plus patch: Share.kt package already present")

    def replace_internal_class(path: str) -> bool:
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        updated = content.replace("internal class ", "class ")
        if updated == content:
            return False
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(updated)
        return True

    manager_changed = replace_internal_class(manager_file)
    pending_changed = replace_internal_class(pending_file)

    if manager_changed or pending_changed:
        print("share_plus patch: updated internal class visibility")
    else:
        print("share_plus patch: internal class visibility already updated")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
