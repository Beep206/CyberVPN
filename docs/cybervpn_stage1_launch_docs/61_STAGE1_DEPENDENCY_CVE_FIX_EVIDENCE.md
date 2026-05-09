# Stage 1 Dependency CVE Fix Evidence

> Date: 2026-05-04  
> Scope: targeted remediation before `S1-ADM-001`  
> Status: local Python environment evidence complete; frontend/npm dependency audit remains tracked separately

## Purpose

Close the two targeted Python environment findings raised after `S1-TG-008`:

| Environment | Finding | Remediation |
|---|---|---|
| `services/telegram-bot` | `pip 26.0.1 / CVE-2026-3219` | Upgraded local bot environment to `pip 26.1` |
| `backend` | `pillow 12.1.1 / CVE-2026-40192` | Removed unused `pillow` from backend `.venv`; it is not declared in `backend/pyproject.toml` or `backend/uv.lock` |

## Source Notes

| CVE | Source note |
|---|---|
| `CVE-2026-3219` | NVD describes the pip archive-type ambiguity; GitHub Advisory listed `<=26.0.1` as affected as of 2026-04-24, while PyPI shows `pip 26.1` released on 2026-04-26. Local `pip-audit` is the final control for the environment. |
| `CVE-2026-40192` | NVD/GitLab advisory state Pillow `10.3.0` through `12.1.1` is affected and `12.2.0` is the fixed version. Backend did not need Pillow, so removal is safer than adding an unused dependency. |

## Commands and Results

| Check | Command | Result |
|---|---|---|
| Bot pip upgrade | `cd services/telegram-bot && .venv/bin/python -m pip install --upgrade pip==26.1` | `Successfully installed pip-26.1` |
| Bot version proof | `cd services/telegram-bot && .venv/bin/python -m pip --version` | `pip 26.1` |
| Bot audit | `cd services/telegram-bot && .venv/bin/python -m pip_audit` | `No known vulnerabilities found` |
| Backend Pillow removal | `cd backend && uv pip uninstall pillow` | `Uninstalled 1 package ... pillow==12.1.1` |
| Backend absence proof | `cd backend && .venv/bin/python -m pip show pillow || true` | `WARNING: Package(s) not found: pillow` |
| Backend consistency cleanup | `cd backend && uv pip uninstall opentelemetry-instrumentation-logging` | Removed unused broken extra package `opentelemetry-instrumentation-logging==0.61b0` |
| Bot dependency consistency | `cd services/telegram-bot && .venv/bin/python -m pip check` | `No broken requirements found` |
| Backend dependency consistency | `cd backend && .venv/bin/python -m pip check` | `No broken requirements found` |
| Backend audit | `cd backend && uv run --with pip-audit pip-audit` | `No known vulnerabilities found` |

## Security Notes

- No production secret, provider credential, bot token, VPN config or user data was touched.
- No containers were started for this remediation.
- `backend` does not import `PIL`/`Pillow` or `opentelemetry.instrumentation.logging` in application or test code; the only `PIL` text matches are unrelated identifier substrings.
- If a `.venv` is recreated before RC, rerun the Python dependency audit before tagging.
- `TD-S1-SEC-001` remains open for the broader pre-RC dependency gate, including frontend/npm audit evidence.

## Next ID

Next ID to execute: `S1-ADM-001` - admin domain/access protection.
