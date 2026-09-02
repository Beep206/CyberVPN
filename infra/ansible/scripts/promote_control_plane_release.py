from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
TRUSTED_SIGNER_WORKFLOW = (
    "github.com/Beep206/CyberVPN/.github/workflows/control-plane-images.yml"
)
TRUSTED_SOURCE_REF = "refs/heads/main"
SUPPLY_CHAIN_POLICY_ID = "cybervpn-control-plane-supply-chain/v2"
ACCEPTED_RISK_SCHEMA_ID = "https://cybervpn.dev/schemas/control-plane-accepted-risk/v1"
PROVENANCE_PREDICATE = "https://slsa.dev/provenance/v1"
SBOM_PREDICATE = "https://spdx.dev/Document/v2.3"
SCAN_PREDICATE = "https://cybervpn.dev/attestations/vulnerability-scan/v1"

DIGEST_PATTERN = re.compile(r"^[a-f0-9]{64}$")
SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")
SOURCE_COMMIT_PATTERN = re.compile(r"^[a-f0-9]{40}$")
SOURCE_RUN_URL_PATTERN = re.compile(
    r"^https://github[.]com/Beep206/CyberVPN/actions/runs/[0-9]+$"
)
DECISION_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,127}$")
EVIDENCE_KEYS = {
    "schema_version",
    "policy_id",
    "source_commit",
    "source_run_url",
    "source_ref",
    "signer_workflow",
    "accepted_risk",
    "components",
}
CLAIM_KEYS = {
    "verified",
    "verification_method",
    "predicate_type",
    "signer_workflow",
    "verification_output_sha256",
    "attestation_count",
}
SCAN_FACT_KEYS = {
    "schema_version",
    "policy_id",
    "result",
    "critical",
    "high",
    "scanner",
    "report_format",
    "report_sha256",
    "subject",
    "risk_disposition",
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


def validate_image_ref(component: str, image_ref: str) -> str:
    expected_prefix = f"{EXPECTED_IMAGE_REPOSITORIES[component]}@sha256:"
    if not image_ref.startswith(expected_prefix):
        raise RuntimeError(
            f"{component} image must use the reviewed repository "
            f"{EXPECTED_IMAGE_REPOSITORIES[component]}."
        )
    digest = image_ref.removeprefix(expected_prefix)
    if not DIGEST_PATTERN.fullmatch(digest):
        raise RuntimeError(f"{component} image must be pinned by a sha256 digest.")
    return digest


def validate_source_metadata(source_commit: str, source_run_url: str) -> None:
    if not SOURCE_COMMIT_PATTERN.fullmatch(source_commit):
        raise RuntimeError(
            "Source commit must be exactly 40 lowercase hexadecimal characters."
        )
    if not SOURCE_RUN_URL_PATTERN.fullmatch(source_run_url):
        raise RuntimeError(
            "Source run URL must identify a Beep206/CyberVPN GitHub Actions run."
        )


def default_release_name(environment: str, source_commit: str, created_at: str) -> str:
    timestamp = (
        created_at.replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")
    )
    return f"control-plane-{environment}-{timestamp}-{source_commit[:12]}"


def load_evidence_manifest(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size > 10 * 1024 * 1024:
            raise RuntimeError("Supply-chain evidence manifest exceeds 10 MiB.")
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"Unable to read supply-chain evidence manifest: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Supply-chain evidence manifest must be a JSON object.")
    return payload


def _require_verified_claim(
    *,
    component: str,
    claim_name: str,
    claim: object,
    predicate_type: str,
) -> dict[str, Any]:
    if not isinstance(claim, dict) or set(claim) != CLAIM_KEYS:
        raise RuntimeError(f"{component} {claim_name} evidence schema is malformed.")
    if claim.get("verified") is not True:
        raise RuntimeError(f"{component} {claim_name} evidence is not verified.")
    if claim.get("verification_method") != "gh-attestation-verify":
        raise RuntimeError(
            f"{component} {claim_name} must be verified with gh attestation verify."
        )
    if claim.get("predicate_type") != predicate_type:
        raise RuntimeError(f"{component} {claim_name} predicate type is not allowed.")
    if claim.get("signer_workflow") != TRUSTED_SIGNER_WORKFLOW:
        raise RuntimeError(
            f"{component} {claim_name} signer workflow does not match policy."
        )
    output_sha256 = claim.get("verification_output_sha256")
    if not isinstance(output_sha256, str) or not SHA256_HEX_PATTERN.fullmatch(
        output_sha256
    ):
        raise RuntimeError(
            f"{component} {claim_name} verification output digest is malformed."
        )
    count = claim.get("attestation_count")
    if type(count) is not int or count < 1:
        raise RuntimeError(f"{component} {claim_name} attestation count is malformed.")
    return claim


def _validated_scan(*, component: str, image: str, scan: object) -> dict[str, Any]:
    expected_keys = CLAIM_KEYS | SCAN_FACT_KEYS
    if not isinstance(scan, dict):
        raise RuntimeError(f"{component} vulnerability scan evidence is malformed.")
    has_decision = "accepted_risk_decision_id" in scan
    if set(scan) != expected_keys | (
        {"accepted_risk_decision_id"} if has_decision else set()
    ):
        raise RuntimeError(
            f"{component} vulnerability scan evidence schema is malformed."
        )
    _require_verified_claim(
        component=component,
        claim_name="vulnerability scan",
        claim={key: scan[key] for key in CLAIM_KEYS},
        predicate_type=SCAN_PREDICATE,
    )
    if scan.get("schema_version") != 2:
        raise RuntimeError(f"{component} vulnerability scan schema version is invalid.")
    if scan.get("policy_id") != SUPPLY_CHAIN_POLICY_ID:
        raise RuntimeError(f"{component} vulnerability scan policy is invalid.")
    if scan.get("subject") != image:
        raise RuntimeError(f"{component} vulnerability scan subject does not match.")
    scanner = scan.get("scanner")
    if scanner not in {"trivy", "docker-scout"}:
        raise RuntimeError(f"{component} vulnerability scanner is not allowed.")
    if (
        scan.get("report_format")
        != {
            "trivy": "trivy-json",
            "docker-scout": "docker-scout-json",
        }[scanner]
    ):
        raise RuntimeError(f"{component} vulnerability report format is invalid.")
    report_sha256 = scan.get("report_sha256")
    if not isinstance(report_sha256, str) or not SHA256_HEX_PATTERN.fullmatch(
        report_sha256
    ):
        raise RuntimeError(f"{component} vulnerability report digest is invalid.")
    critical = scan.get("critical")
    high = scan.get("high")
    if type(critical) is not int or critical < 0:
        raise RuntimeError(f"{component} vulnerability critical count is invalid.")
    if type(high) is not int or high < 0:
        raise RuntimeError(f"{component} vulnerability high count is invalid.")
    has_findings = critical > 0 or high > 0
    if scan.get("result") != ("findings" if has_findings else "pass"):
        raise RuntimeError(f"{component} vulnerability result/count mismatch.")
    if scan.get("risk_disposition") != (
        "accepted_non_blocking" if has_findings else "clean"
    ):
        raise RuntimeError(f"{component} vulnerability risk disposition is invalid.")
    decision_id = scan.get("accepted_risk_decision_id")
    if has_findings:
        if not isinstance(decision_id, str) or not DECISION_ID_PATTERN.fullmatch(
            decision_id
        ):
            raise RuntimeError(
                f"{component} accepted-risk decision reference is malformed."
            )
    elif has_decision:
        raise RuntimeError(f"{component} clean scan cannot reference accepted risk.")
    return scan


def _validate_accepted_risk(
    *,
    decision: object,
    source_commit: str,
    images: dict[str, str],
    scans: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    finding_components = {
        component
        for component, scan in scans.items()
        if scan["critical"] > 0 or scan["high"] > 0
    }
    if not finding_components:
        if decision is not None:
            raise RuntimeError("Accepted-risk decision is stale for a clean release.")
        return None
    if not isinstance(decision, dict) or set(decision) != RISK_DECISION_KEYS:
        raise RuntimeError("Accepted-risk decision schema is malformed.")
    if decision.get("schema_version") != 1:
        raise RuntimeError("Accepted-risk schema_version must equal 1.")
    if decision.get("schema_id") != ACCEPTED_RISK_SCHEMA_ID:
        raise RuntimeError("Accepted-risk schema identity mismatch.")
    if decision.get("decision") != "accepted_non_blocking":
        raise RuntimeError("Accepted-risk decision value is invalid.")
    if decision.get("policy_id") != SUPPLY_CHAIN_POLICY_ID:
        raise RuntimeError("Accepted-risk policy identity mismatch.")
    if decision.get("signer_workflow") != TRUSTED_SIGNER_WORKFLOW:
        raise RuntimeError("Accepted-risk signer workflow mismatch.")
    if decision.get("source_commit") != source_commit:
        raise RuntimeError("Accepted-risk source commit mismatch.")
    decision_id = decision.get("decision_id")
    if not isinstance(decision_id, str) or not DECISION_ID_PATTERN.fullmatch(
        decision_id
    ):
        raise RuntimeError("Accepted-risk decision_id is malformed.")
    if not isinstance(decision.get("approved_by"), str) or not (
        3 <= len(decision["approved_by"]) <= 128
    ):
        raise RuntimeError("Accepted-risk approved_by is malformed.")
    approved_at = decision.get("approved_at")
    if not isinstance(approved_at, str) or not approved_at.endswith("Z"):
        raise RuntimeError("Accepted-risk approved_at is malformed.")
    try:
        datetime.fromisoformat(approved_at.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise RuntimeError("Accepted-risk approved_at is malformed.") from exc
    rationale = decision.get("rationale")
    if not isinstance(rationale, str) or not (20 <= len(rationale) <= 2000):
        raise RuntimeError("Accepted-risk rationale is malformed.")
    components = decision.get("components")
    if not isinstance(components, dict) or set(components) != finding_components:
        raise RuntimeError(
            "Accepted-risk components must exactly match verified scan findings."
        )
    for component in finding_components:
        item = components.get(component)
        if not isinstance(item, dict) or set(item) != RISK_COMPONENT_KEYS:
            raise RuntimeError(
                f"Accepted-risk component schema is malformed for {component}."
            )
        scan = scans[component]
        expected = {
            "image": images[component],
            "scanner": scan["scanner"],
            "report_sha256": scan["report_sha256"],
            "critical": scan["critical"],
            "high": scan["high"],
        }
        if item != expected:
            raise RuntimeError(
                f"Accepted-risk facts do not match the signed scan for {component}."
            )
        if scan["accepted_risk_decision_id"] != decision_id:
            raise RuntimeError(
                f"Accepted-risk decision reference mismatch for {component}."
            )
    return decision


def validate_supply_chain_evidence(
    *,
    evidence: dict[str, Any],
    images: dict[str, str],
    source_commit: str,
    source_run_url: str,
    signer_workflow: str = TRUSTED_SIGNER_WORKFLOW,
) -> dict[str, Any]:
    if signer_workflow != TRUSTED_SIGNER_WORKFLOW:
        raise RuntimeError("Signer workflow is not the fixed CyberVPN identity.")
    if set(evidence) != EVIDENCE_KEYS:
        raise RuntimeError("Supply-chain evidence schema is malformed.")
    if evidence.get("schema_version") != 2:
        raise RuntimeError("Supply-chain evidence schema_version must equal 2.")
    if evidence.get("policy_id") != SUPPLY_CHAIN_POLICY_ID:
        raise RuntimeError("Supply-chain evidence policy identity mismatch.")
    if evidence.get("source_commit") != source_commit:
        raise RuntimeError("Supply-chain evidence source commit does not match.")
    if evidence.get("source_run_url") != source_run_url:
        raise RuntimeError("Supply-chain evidence run URL does not match.")
    if evidence.get("source_ref") != TRUSTED_SOURCE_REF:
        raise RuntimeError("Supply-chain evidence source ref does not match policy.")
    if evidence.get("signer_workflow") != TRUSTED_SIGNER_WORKFLOW:
        raise RuntimeError("Supply-chain evidence signer workflow does not match.")

    components = evidence.get("components")
    if not isinstance(components, dict) or set(components) != set(RELEASE_COMPONENTS):
        raise RuntimeError(
            "Supply-chain evidence must contain exactly every release component."
        )
    normalized_components: dict[str, Any] = {}
    scans: dict[str, dict[str, Any]] = {}
    for component in RELEASE_COMPONENTS:
        item = components.get(component)
        if not isinstance(item, dict) or set(item) != {
            "image",
            "provenance",
            "sbom",
            "vulnerability_scan",
        }:
            raise RuntimeError(
                f"Supply-chain component schema is malformed for {component}."
            )
        if item.get("image") != images[component]:
            raise RuntimeError(
                f"Supply-chain evidence image for {component} does not match."
            )
        provenance = _require_verified_claim(
            component=component,
            claim_name="provenance",
            claim=item.get("provenance"),
            predicate_type=PROVENANCE_PREDICATE,
        )
        sbom = _require_verified_claim(
            component=component,
            claim_name="SBOM",
            claim=item.get("sbom"),
            predicate_type=SBOM_PREDICATE,
        )
        scan = _validated_scan(
            component=component,
            image=images[component],
            scan=item.get("vulnerability_scan"),
        )
        scans[component] = scan
        normalized_components[component] = {
            "image": images[component],
            "provenance": provenance,
            "sbom": sbom,
            "vulnerability_scan": scan,
        }

    accepted_risk = _validate_accepted_risk(
        decision=evidence.get("accepted_risk"),
        source_commit=source_commit,
        images=images,
        scans=scans,
    )
    return {
        "policy_version": 2,
        "policy_id": SUPPLY_CHAIN_POLICY_ID,
        "signer_workflow": TRUSTED_SIGNER_WORKFLOW,
        "source_ref": TRUSTED_SOURCE_REF,
        "accepted_risk": accepted_risk,
        "components": normalized_components,
    }


def build_release_manifest(
    *,
    environment: str,
    remnawave_image: str,
    remnawave_auth_secret_sha256: str,
    backend_image: str,
    worker_image: str,
    helix_adapter_image: str,
    node_image: str,
    subscription_page_image: str,
    node_ssh_proxy_image: str,
    source_commit: str,
    source_run_url: str,
    created_at: str,
    release_name: str,
    evidence: dict[str, Any],
    signer_workflow: str = TRUSTED_SIGNER_WORKFLOW,
) -> dict[str, Any]:
    images = {
        "remnawave": remnawave_image,
        "backend": backend_image,
        "worker": worker_image,
        "helix_adapter": helix_adapter_image,
        "node": node_image,
        "subscription_page": subscription_page_image,
        "node_ssh_proxy": node_ssh_proxy_image,
    }
    digests: set[str] = set()
    for component, image_ref in images.items():
        digest = validate_image_ref(component, image_ref)
        if digest in digests:
            raise RuntimeError(
                f"{component} image reuses another release component digest."
            )
        digests.add(digest)
    if not SHA256_HEX_PATTERN.fullmatch(remnawave_auth_secret_sha256):
        raise RuntimeError(
            "Remnawave pre-upgrade auth secret fingerprint must be 64 lowercase hex characters."
        )
    validate_source_metadata(source_commit, source_run_url)
    supply_chain = validate_supply_chain_evidence(
        evidence=evidence,
        images=images,
        source_commit=source_commit,
        source_run_url=source_run_url,
        signer_workflow=signer_workflow,
    )
    canonical_evidence = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    supply_chain["evidence_sha256"] = hashlib.sha256(canonical_evidence).hexdigest()

    effective_release_name = release_name or default_release_name(
        environment=environment,
        source_commit=source_commit,
        created_at=created_at,
    )
    return {
        "control_plane_release_name": effective_release_name,
        "control_plane_release_source_commit": source_commit,
        "control_plane_release_source_run_url": source_run_url,
        "control_plane_release_created_at": created_at,
        "control_plane_remnawave_preupgrade_auth_secret_sha256": (
            remnawave_auth_secret_sha256
        ),
        "control_plane_release_images": images,
        "control_plane_release_supply_chain": supply_chain,
    }


def write_json_yaml(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON, which remains valid YAML for Ansible without PyYAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a verified, digest-pinned control-plane release manifest."
    )
    parser.add_argument(
        "--environment", required=True, choices=("staging", "production")
    )
    parser.add_argument(
        "--inventory-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "inventories",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--remnawave-image", required=True)
    parser.add_argument("--remnawave-auth-secret-sha256", required=True)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--worker-image", required=True)
    parser.add_argument("--helix-adapter-image", required=True)
    parser.add_argument("--node-image", required=True)
    parser.add_argument("--subscription-page-image", required=True)
    parser.add_argument("--node-ssh-proxy-image", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-run-url", required=True)
    parser.add_argument("--evidence-manifest", required=True, type=Path)
    parser.add_argument(
        "--signer-workflow",
        default=TRUSTED_SIGNER_WORKFLOW,
        help="Compatibility flag; only the fixed CyberVPN signer is accepted.",
    )
    parser.add_argument(
        "--created-at",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    parser.add_argument("--release-name", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output or (
        args.inventory_root
        / args.environment
        / "group_vars"
        / f"control_plane_{args.environment}"
        / "release.yml"
    )
    payload = build_release_manifest(
        environment=args.environment,
        remnawave_image=args.remnawave_image,
        remnawave_auth_secret_sha256=args.remnawave_auth_secret_sha256,
        backend_image=args.backend_image,
        worker_image=args.worker_image,
        helix_adapter_image=args.helix_adapter_image,
        node_image=args.node_image,
        subscription_page_image=args.subscription_page_image,
        node_ssh_proxy_image=args.node_ssh_proxy_image,
        source_commit=args.source_commit,
        source_run_url=args.source_run_url,
        created_at=args.created_at,
        release_name=args.release_name,
        evidence=load_evidence_manifest(args.evidence_manifest),
        signer_workflow=args.signer_workflow,
    )
    write_json_yaml(output_path, payload)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
