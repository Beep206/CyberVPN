from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from policy_compiler.compiler import GeneratedDriftError, check_generated, generate
    from policy_compiler.loader import PolicyLoadError
    from policy_compiler.source_verifier import (
        SourceVerificationError,
        verify_remote_sources,
    )
else:
    from .compiler import GeneratedDriftError, check_generated, generate
    from .loader import PolicyLoadError
    from .source_verifier import SourceVerificationError, verify_remote_sources


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile canonical CyberVPN Remnawave policies"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "check"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--policy", required=True, type=Path)
        subparser.add_argument("--output-dir", type=Path)
    verify_parser = subparsers.add_parser("verify-sources")
    verify_parser.add_argument("--policy", required=True, type=Path)
    verify_parser.add_argument("--timeout", type=float, default=30.0)
    verify_parser.add_argument("--max-source-bytes", type=int, default=64 * 1024 * 1024)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify-sources":
            verified = verify_remote_sources(
                args.policy,
                timeout_seconds=args.timeout,
                max_source_bytes=args.max_source_bytes,
            )
            print(
                json.dumps(
                    {
                        "status": "verified",
                        "sources": [
                            {
                                "id": item.source_id,
                                "bytes": item.bytes,
                                "sha256": item.sha256,
                            }
                            for item in verified
                        ],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "generate":
            result = generate(args.policy, args.output_dir)
            status = "generated" if result.changed else "unchanged"
        else:
            result = check_generated(args.policy, args.output_dir)
            status = "clean"
    except (GeneratedDriftError, PolicyLoadError, SourceVerificationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "status": status,
                "outputDir": str(result.output_dir),
                "changed": [str(path) for path in result.changed],
                "policySha256": result.policy_sha256,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
