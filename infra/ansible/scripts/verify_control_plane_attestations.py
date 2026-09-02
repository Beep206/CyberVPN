from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any


TRUSTED_REPOSITORY = "Beep206/CyberVPN"
TRUSTED_SIGNER_WORKFLOW = (
    "github.com/Beep206/CyberVPN/.github/workflows/control-plane-images.yml"
)
TRUSTED_SOURCE_REF = "refs/heads/main"
SUPPLY_CHAIN_POLICY_ID = "cybervpn-control-plane-supply-chain/v2"
ACCEPTED_RISK_SCHEMA_ID = "https://cybervpn.dev/schemas/control-plane-accepted-risk/v1"
RELEASE_COMPONENTS = (
    "remnawave",
    "backend",
    "worker",
    "helix_adapter",
    "node",
    "subscription_page",
    "node_ssh_proxy",
)
EXPECTED_IMAGE_REPOSITORIES = {
    "remnawave": "ghcr.io/beep206/cybervpn/remnawave-backend",
    "backend": "ghcr.io/beep206/cybervpn/backend",
    "worker": "ghcr.io/beep206/cybervpn/task-worker",
    "helix_adapter": "ghcr.io/beep206/cybervpn/helix-adapter",
    "node": "ghcr.io/beep206/cybervpn/remnawave-node",
    "subscription_page": ("ghcr.io/beep206/cybervpn/remnawave-subscription-page"),
    "node_ssh_proxy": "ghcr.io/beep206/cybervpn/node-ssh-proxy",
}
PREDICATES = {
    "provenance": "https://slsa.dev/provenance/v1",
    "sbom": "https://spdx.dev/Document/v2.3",
    "vulnerability_scan": ("https://cybervpn.dev/attestations/vulnerability-scan/v1"),
}

DIGEST_PATTERN = re.compile(r"^[a-f0-9]{64}$")
SOURCE_COMMIT_PATTERN = re.compile(r"^[a-f0-9]{40}$")
DECISION_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,127}$")
SOURCE_RUN_URL_PATTERN = re.compile(
    r"^https://github[.]com/Beep206/CyberVPN/actions/runs/[0-9]+$"
)
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
MAX_VERIFICATION_OUTPUT_BYTES = 64 * 1024 * 1024
Runner = Callable[..., subprocess.CompletedProcess[str]]

SCAN_PREDICATE_KEYS = {
    "schema_version",
    "policy_id",
    "result",
    "critical",
    "high",
    "scanner",
    "report_format",
    "report_sha256",
    "subject",
}
RISK_DECISION_KEYS = {
    "schema_version",
    "schema_id",
    "decision_id",
    "decision",
    "policy_id",
    "approved_by",
    "approved_at",
    "rationale",
    "signer_workflow",
    "source_commit",
    "components",
}
RISK_COMPONENT_KEYS = {
    "image",
    "scanner",
    "report_sha256",
    "critical",
    "high",
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def _load_json(raw: str, *, description: str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"invalid {description} JSON: {exc}") from exc


def _validate_component_image(component: str, image: str) -> str:
    expected_prefix = f"{EXPECTED_IMAGE_REPOSITORIES[component]}@sha256:"
    if not image.startswith(expected_prefix):
        raise ValueError(
            f"{component} image must use the reviewed repository "
            f"{EXPECTED_IMAGE_REPOSITORIES[component]}"
        )
    digest = image.removeprefix(expected_prefix)
    if not DIGEST_PATTERN.fullmatch(digest):
        raise ValueError(f"{component} image must be pinned by a sha256 digest")
    return digest


def _parse_component_image(value: str) -> tuple[str, str]:
    component, separator, image = value.partition("=")
    if not separator or component not in RELEASE_COMPONENTS:
        raise argparse.ArgumentTypeError(
            "--image must use one of the reviewed component names as component=ref"
        )
    try:
        _validate_component_image(component, image)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return component, image


def _load_verification_result(
    *, component: str, claim: str, stdout: str
) -> list[dict[str, Any]]:
    payload = _load_json(
        stdout,
        description=f"gh {component} {claim} verification output",
    )
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"no verified {claim} attestation found for {component}")
    if not all(isinstance(entry, dict) for entry in payload):
        raise RuntimeError(f"unexpected gh verification result for {component} {claim}")
    return payload


def _validated_statement(
    *,
    entry: Mapping[str, Any],
    component: str,
    claim: str,
    predicate_type: str,
    image: str,
) -> Mapping[str, Any]:
    verification = entry.get("verificationResult")
    if not isinstance(verification, Mapping):
        raise RuntimeError(f"malformed verified {claim} attestation for {component}")
    statement = verification.get("statement")
    if not isinstance(statement, Mapping):
        raise RuntimeError(f"malformed verified {claim} statement for {component}")
    if statement.get("predicateType") != predicate_type:
        raise RuntimeError(f"verified {claim} predicate type mismatch for {component}")

    subject_name, _, digest = image.rpartition("@sha256:")
    subjects = statement.get("subject")
    if not isinstance(subjects, list) or not subjects:
        raise RuntimeError(f"verified {claim} statement has no subject for {component}")
    subject_matches = any(
        isinstance(subject, Mapping)
        and subject.get("name") == subject_name
        and isinstance(subject.get("digest"), Mapping)
        and subject["digest"].get("sha256") == digest
        for subject in subjects
    )
    if not subject_matches:
        raise RuntimeError(
            f"verified {claim} statement subject mismatch for {component}"
        )

    predicate = statement.get("predicate")
    if not isinstance(predicate, Mapping):
        raise RuntimeError(f"verified {claim} predicate is malformed for {component}")
    return predicate


def _validate_provenance_predicate(
    *, component: str, predicate: Mapping[str, Any]
) -> None:
    if not isinstance(predicate.get("buildDefinition"), Mapping):
        raise RuntimeError(
            f"verified provenance buildDefinition is malformed for {component}"
        )
    if not isinstance(predicate.get("runDetails"), Mapping):
        raise RuntimeError(
            f"verified provenance runDetails is malformed for {component}"
        )


def _validate_sbom_predicate(*, component: str, predicate: Mapping[str, Any]) -> None:
    if predicate.get("spdxVersion") != "SPDX-2.3":
        raise RuntimeError(f"verified SBOM is not an SPDX-2.3 document for {component}")
    if predicate.get("SPDXID") != "SPDXRef-DOCUMENT":
        raise RuntimeError(
            f"verified SBOM document identity is malformed for {component}"
        )
    if not isinstance(predicate.get("packages"), list):
        raise RuntimeError(f"verified SBOM packages are malformed for {component}")


def _validated_scan_predicate(
    *, component: str, image: str, predicate: Mapping[str, Any]
) -> dict[str, Any]:
    if set(predicate) != SCAN_PREDICATE_KEYS:
        raise RuntimeError(
            f"verified vulnerability scan schema is malformed for {component}"
        )
    if predicate.get("schema_version") != 2:
        raise RuntimeError(
            f"verified vulnerability scan schema version mismatch for {component}"
        )
    if predicate.get("policy_id") != SUPPLY_CHAIN_POLICY_ID:
        raise RuntimeError(
            f"verified vulnerability scan policy mismatch for {component}"
        )
    if predicate.get("subject") != image:
        raise RuntimeError(
            f"verified vulnerability scan subject mismatch for {component}"
        )
    scanner = predicate.get("scanner")
    report_format = predicate.get("report_format")
    if scanner not in {"trivy", "docker-scout"}:
        raise RuntimeError(
            f"verified vulnerability scanner is not allowed for {component}"
        )
    expected_report_format = {
        "trivy": "trivy-json",
        "docker-scout": "docker-scout-json",
    }[scanner]
    if report_format != expected_report_format:
        raise RuntimeError(
            f"verified vulnerability report format mismatch for {component}"
        )
    report_sha256 = predicate.get("report_sha256")
    if not isinstance(report_sha256, str) or not SHA256_PATTERN.fullmatch(
        report_sha256
    ):
        raise RuntimeError(
            f"verified vulnerability report digest is malformed for {component}"
        )
    critical = predicate.get("critical")
    high = predicate.get("high")
    if type(critical) is not int or critical < 0:
        raise RuntimeError(
            f"verified vulnerability critical count is malformed for {component}"
        )
    if type(high) is not int or high < 0:
        raise RuntimeError(
            f"verified vulnerability high count is malformed for {component}"
        )
    expected_result = "pass" if critical == 0 and high == 0 else "findings"
    if predicate.get("result") != expected_result:
        raise RuntimeError(
            f"verified vulnerability scan result/count mismatch for {component}"
        )
    return dict(predicate)


def _validate_utc_timestamp(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RuntimeError(f"accepted-risk {field} must be an RFC3339 UTC timestamp")
    try:
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise RuntimeError(
            f"accepted-risk {field} must be an RFC3339 UTC timestamp"
        ) from exc
    return value


def validate_accepted_risk_decision(
    *,
    decision: object,
    source_commit: str,
    images: Mapping[str, str],
    scans: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    finding_components = {
        component
        for component, scan in scans.items()
        if scan["critical"] > 0 or scan["high"] > 0
    }
    if not finding_components:
        if decision is not None:
            raise RuntimeError(
                "accepted-risk decision is stale because every verified scan is clean"
            )
        return None
    if not isinstance(decision, Mapping):
        raise RuntimeError(
            "a schema-valid accepted-risk decision is required for scan findings"
        )
    if set(decision) != RISK_DECISION_KEYS:
        raise RuntimeError("accepted-risk decision schema is malformed")
    if decision.get("schema_version") != 1:
        raise RuntimeError("accepted-risk schema_version must equal 1")
    if decision.get("schema_id") != ACCEPTED_RISK_SCHEMA_ID:
        raise RuntimeError("accepted-risk schema identity mismatch")
    if decision.get("policy_id") != SUPPLY_CHAIN_POLICY_ID:
        raise RuntimeError("accepted-risk supply-chain policy mismatch")
    if decision.get("decision") != "accepted_non_blocking":
        raise RuntimeError("accepted-risk decision must be accepted_non_blocking")
    if decision.get("signer_workflow") != TRUSTED_SIGNER_WORKFLOW:
        raise RuntimeError("accepted-risk signer workflow mismatch")
    if decision.get("source_commit") != source_commit:
        raise RuntimeError("accepted-risk source commit mismatch")

    decision_id = decision.get("decision_id")
    if not isinstance(decision_id, str) or not DECISION_ID_PATTERN.fullmatch(
        decision_id
    ):
        raise RuntimeError("accepted-risk decision_id is malformed")
    approved_by = decision.get("approved_by")
    if not isinstance(approved_by, str) or not (3 <= len(approved_by) <= 128):
        raise RuntimeError("accepted-risk approved_by is malformed")
    _validate_utc_timestamp(decision.get("approved_at"), field="approved_at")
    rationale = decision.get("rationale")
    if not isinstance(rationale, str) or not (20 <= len(rationale) <= 2000):
        raise RuntimeError("accepted-risk rationale must contain 20-2000 characters")

    components = decision.get("components")
    if not isinstance(components, Mapping) or set(components) != finding_components:
        raise RuntimeError(
            "accepted-risk components must exactly match verified scan findings"
        )
    normalized_components: dict[str, Any] = {}
    for component in sorted(finding_components):
        item = components.get(component)
        if not isinstance(item, Mapping) or set(item) != RISK_COMPONENT_KEYS:
            raise RuntimeError(
                f"accepted-risk component schema is malformed for {component}"
            )
        scan = scans[component]
        expected = {
            "image": images[component],
            "scanner": scan["scanner"],
            "report_sha256": scan["report_sha256"],
            "critical": scan["critical"],
            "high": scan["high"],
        }
        if dict(item) != expected:
            raise RuntimeError(
                f"accepted-risk decision does not match signed scan facts for {component}"
            )
        normalized_components[component] = expected

    return {
        "schema_version": 1,
        "schema_id": ACCEPTED_RISK_SCHEMA_ID,
        "decision_id": decision_id,
        "decision": "accepted_non_blocking",
        "policy_id": SUPPLY_CHAIN_POLICY_ID,
        "approved_by": approved_by,
        "approved_at": decision["approved_at"],
        "rationale": rationale,
        "signer_workflow": TRUSTED_SIGNER_WORKFLOW,
        "source_commit": source_commit,
        "components": normalized_components,
    }


def _verified_claim(
    *,
    component: str,
    claim: str,
    image: str,
    predicate_type: str,
    stdout: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    verified = _load_verification_result(
        component=component,
        claim=claim,
        stdout=stdout,
    )
    scan_facts: list[dict[str, Any]] = []
    for entry in verified:
        predicate = _validated_statement(
            entry=entry,
            component=component,
            claim=claim,
            predicate_type=predicate_type,
            image=image,
        )
        if claim == "provenance":
            _validate_provenance_predicate(
                component=component,
                predicate=predicate,
            )
        elif claim == "sbom":
            _validate_sbom_predicate(
                component=component,
                predicate=predicate,
            )
        else:
            scan_facts.append(
                _validated_scan_predicate(
                    component=component,
                    image=image,
                    predicate=predicate,
                )
            )

    claim_evidence: dict[str, Any] = {
        "verified": True,
        "verification_method": "gh-attestation-verify",
        "predicate_type": predicate_type,
        "signer_workflow": TRUSTED_SIGNER_WORKFLOW,
        "verification_output_sha256": hashlib.sha256(
            stdout.encode("utf-8")
        ).hexdigest(),
        "attestation_count": len(verified),
    }
    if claim != "vulnerability_scan":
        return claim_evidence, None

    canonical_scans = {
        json.dumps(scan, sort_keys=True, separators=(",", ":")) for scan in scan_facts
    }
    if len(canonical_scans) != 1:
        raise RuntimeError(
            f"verified vulnerability scan attestations disagree for {component}"
        )
    return claim_evidence, scan_facts[0]


def verify_attestations(
    *,
    source_commit: str,
    images: Mapping[str, str],
    gh_bin: str,
    accepted_risk_decision: object = None,
    source_run_url: str = "",
    verification_output_dir: Path | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Verify every digest and return a policy-bound evidence manifest."""
    if not SOURCE_COMMIT_PATTERN.fullmatch(source_commit):
        raise RuntimeError(
            "source commit must be exactly 40 lowercase hexadecimal characters"
        )
    if source_run_url and not SOURCE_RUN_URL_PATTERN.fullmatch(source_run_url):
        raise RuntimeError(
            "source run URL must identify a Beep206/CyberVPN GitHub Actions run"
        )
    if set(images) != set(RELEASE_COMPONENTS):
        raise RuntimeError(
            "images must contain exactly every reviewed control-plane component"
        )

    digests: set[str] = set()
    for component in RELEASE_COMPONENTS:
        image = images[component]
        try:
            digest = _validate_component_image(component, image)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc
        if digest in digests:
            raise RuntimeError(
                f"{component} image reuses another release component digest"
            )
        digests.add(digest)

    if verification_output_dir is not None:
        verification_output_dir.mkdir(parents=True, exist_ok=True)

    components: dict[str, Any] = {}
    scans: dict[str, dict[str, Any]] = {}
    for component in RELEASE_COMPONENTS:
        image = images[component]
        component_evidence: dict[str, Any] = {"image": image}
        for claim, predicate_type in PREDICATES.items():
            command = [
                gh_bin,
                "attestation",
                "verify",
                f"oci://{image}",
                "--repo",
                TRUSTED_REPOSITORY,
                "--signer-workflow",
                TRUSTED_SIGNER_WORKFLOW,
                "--source-ref",
                TRUSTED_SOURCE_REF,
                "--source-digest",
                source_commit,
                "--deny-self-hosted-runners",
                "--predicate-type",
                predicate_type,
                "--format",
                "json",
            ]
            try:
                result = runner(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError(
                    f"unable to verify {component} {claim} attestation"
                ) from exc
            if result.returncode != 0:
                raise RuntimeError(
                    f"cryptographic verification failed for {component} {claim}"
                )
            if len(result.stdout.encode("utf-8")) > MAX_VERIFICATION_OUTPUT_BYTES:
                raise RuntimeError(
                    f"verified {component} {claim} output exceeds 64 MiB"
                )
            claim_evidence, scan = _verified_claim(
                component=component,
                claim=claim,
                image=image,
                predicate_type=predicate_type,
                stdout=result.stdout,
            )
            component_evidence[claim] = claim_evidence
            if scan is not None:
                scans[component] = scan
            if verification_output_dir is not None:
                output_path = verification_output_dir / f"{component}-{claim}.json"
                output_path.write_text(result.stdout, encoding="utf-8")
        components[component] = component_evidence

    accepted_risk = validate_accepted_risk_decision(
        decision=accepted_risk_decision,
        source_commit=source_commit,
        images=images,
        scans=scans,
    )
    accepted_risk_id = (
        accepted_risk["decision_id"] if accepted_risk is not None else None
    )
    for component, scan in scans.items():
        has_findings = scan["critical"] > 0 or scan["high"] > 0
        components[component]["vulnerability_scan"].update(scan)
        components[component]["vulnerability_scan"]["risk_disposition"] = (
            "accepted_non_blocking" if has_findings else "clean"
        )
        if has_findings:
            components[component]["vulnerability_scan"]["accepted_risk_decision_id"] = (
                accepted_risk_id
            )

    return {
        "schema_version": 2,
        "policy_id": SUPPLY_CHAIN_POLICY_ID,
        "source_commit": source_commit,
        "source_run_url": source_run_url,
        "source_ref": TRUSTED_SOURCE_REF,
        "signer_workflow": TRUSTED_SIGNER_WORKFLOW,
        "accepted_risk": accepted_risk,
        "components": components,
    }


def load_accepted_risk_decision(value: str | None) -> object:
    if value is None:
        return None
    if value == "-":
        raw = sys.stdin.read(131_073)
    else:
        path = Path(value)
        try:
            if path.stat().st_size > 131_072:
                raise RuntimeError("accepted-risk decision exceeds 128 KiB")
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"unable to read accepted-risk decision: {exc}") from exc
    if len(raw.encode("utf-8")) > 131_072:
        raise RuntimeError("accepted-risk decision exceeds 128 KiB")
    return _load_json(raw, description="accepted-risk decision")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed verification of CyberVPN control-plane OCI attestations "
            "and exact digest-bound accepted-risk decisions."
        )
    )
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-run-url", default="")
    parser.add_argument(
        "--image",
        action="append",
        required=True,
        type=_parse_component_image,
        help="Reviewed component and digest ref, for example backend=...@sha256:...",
    )
    parser.add_argument(
        "--accepted-risk-decision",
        help="Path to a decision JSON file, or '-' to read JSON/null from stdin.",
    )
    parser.add_argument("--verification-output-dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    images: dict[str, str] = {}
    for component, image in args.image:
        if component in images:
            raise RuntimeError(f"duplicate image component: {component}")
        images[component] = image

    gh_bin = shutil.which("gh")
    if not gh_bin:
        raise RuntimeError(
            "GitHub CLI is required on the Ansible controller for attestation verification"
        )
    evidence = verify_attestations(
        source_commit=args.source_commit,
        source_run_url=args.source_run_url,
        images=images,
        gh_bin=gh_bin,
        accepted_risk_decision=load_accepted_risk_decision(args.accepted_risk_decision),
        verification_output_dir=args.verification_output_dir,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    findings = sum(
        1
        for component in RELEASE_COMPONENTS
        if evidence["components"][component]["vulnerability_scan"]["risk_disposition"]
        == "accepted_non_blocking"
    )
    print(
        "All seven image identities and signed attestations satisfy policy; "
        f"accepted-risk components: {findings}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
