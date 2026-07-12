import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const DEFAULT_OUTPUT = '.codex/local-runtime/ac33-release-evidence-audit-20260708.json';
const OUTPUT_PATH = readCliOption('output') || process.env.AC33_RELEASE_EVIDENCE_AUDIT_OUTPUT || DEFAULT_OUTPUT;

const checks = [];

const currentTask = readJson('.codex/current-task.json');
const ac33 = currentTask.acceptance_criteria?.find((criterion) => criterion.id === 'AC-33');
const validations = currentTask.validations ?? [];
const summary = readJson('.codex/command-logs/20260708T055037Z/summary.json');
const stage1DryRun = readText('.codex/local-runtime/ac33-stage1-dry-run/stage1-gitlab-deploy-local-ac33-20260707T164242Z.md');
const ansibleSyntax = readText('.codex/local-runtime/ac33-ansible-staging-syntax.txt');
const repoIdempotence = readText('.codex/local-runtime/ac33-disposable-repo-idempotence.txt');
const alloyDeploy = readText('.codex/local-runtime/ac33-disposable-alloy-deploy-info.txt');
const alloyRollback = readText('.codex/local-runtime/ac33-disposable-alloy-rollback.txt');
const finalState = readText('.codex/local-runtime/ac33-disposable-final-state.txt');
const codeqlWorkflow = readText('.github/workflows/codeql.yml');
const deployStagingWorkflow = readText('.github/workflows/deploy-staging.yml');
const androidTvReleaseWorkflow = readText('.github/workflows/android-tv-release.yml');
const actionlintEvidence = readText('.codex/local-runtime/ac33-actionlint-20260708.txt');
const codeqlLocalSummary = readJson('.codex/local-runtime/ac33-codeql-local-summary-20260708.json');
const workflowFiles = readWorkflowFiles();

check('current-task status is pass after user-owned AC-33 hosted/staging closure', {
  passed:
    currentTask.status === 'pass' &&
    Array.isArray(currentTask.acceptance_criteria) &&
    currentTask.acceptance_criteria.every((criterion) => criterion.status === 'pass') &&
    Array.isArray(currentTask.unresolved) &&
    currentTask.unresolved.length === 0,
  details: {
    status: currentTask.status,
    acceptanceStatusCounts: countBy(currentTask.acceptance_criteria ?? [], (criterion) => criterion.status ?? 'missing'),
    unresolved: currentTask.unresolved ?? null,
  },
});

check('AC-33 is pass with explicit user-owned hosted CI and staging evidence boundary', {
  passed:
    ac33?.status === 'pass' &&
    includesAny(ac33?.implementation_evidence, ['User explicit closure decision on 2026-07-09']) &&
    includesAny(ac33?.test_evidence, ['PASS_BY_USER_OWNER']) &&
    validations.some(
      (entry) =>
        entry.command?.includes('AC-33 hosted/staging release/rollback/public smoke evidence will be closed by the user') &&
        entry.status === 'pass' &&
        entry.result === 'PASS_BY_USER_OWNER' &&
        entry.exit_code === 0,
    ) &&
    !includesAny(currentTask.unresolved, ['AC-33 remains partial']) &&
    !includesAny(ac33?.test_evidence, ['AC-33 remains partial', 'AC-33 partial boundary']),
  details: {
    ac33Status: ac33?.status ?? null,
    unresolved: currentTask.unresolved ?? [],
    userOwnerEvidenceRecorded: includesAny(ac33?.test_evidence, ['PASS_BY_USER_OWNER']),
    userOwnerValidationRecorded: validations.some((entry) => entry.result === 'PASS_BY_USER_OWNER'),
  },
});

check('legacy top-level validation is absent', {
  passed: !Object.prototype.hasOwnProperty.call(currentTask, 'validation') && Array.isArray(validations),
  details: {
    hasValidation: Object.prototype.hasOwnProperty.call(currentTask, 'validation'),
    validationsCount: validations.length,
  },
});

check('Grafana/Prometheus maintenance context is recorded without local startup', {
  passed:
    includesAny(currentTask.assumptions, ['Grafana/Prometheus home infra server is off for maintenance']) &&
    includesAny(ac33?.implementation_evidence, ['must not be started locally']) &&
    includesAny(ac33?.test_evidence, ['PASS_BY_USER_CONTEXT', 'pass-by-user-context']) &&
    validations.some(
      (entry) =>
        entry.command?.includes('Grafana/Prometheus home infra maintenance') &&
        entry.status === 'pass' &&
        entry.result === 'PASS_BY_USER_CONTEXT',
    ),
  details: {
    assumptionRecorded: includesAny(currentTask.assumptions, ['Grafana/Prometheus home infra server is off for maintenance']),
    implementationRecorded: includesAny(ac33?.implementation_evidence, ['must not be started locally']),
    evidenceRecorded: includesAny(ac33?.test_evidence, ['PASS_BY_USER_CONTEXT', 'pass-by-user-context']),
    validationRecorded: validations.some((entry) => entry.result === 'PASS_BY_USER_CONTEXT'),
  },
});

check('local services/infra/release gate summary passed 35/35', {
  passed:
    summary.pass_count === 35 &&
    summary.fail_count === 0 &&
    Array.isArray(summary.results) &&
    summary.results.length === 35 &&
    summary.results.every((result) => result.status === 'pass' && result.exit_code === 0) &&
    summary.results.some((result) => result.command_label === 'shellcheck') &&
    summary.results.some((result) => result.command_label === 'docker-compose-config'),
  details: {
    createdAt: summary.created_at,
    baseRef: summary.base_ref,
    passCount: summary.pass_count,
    failCount: summary.fail_count,
    resultCount: summary.results?.length ?? null,
    requiredLabels: ['shellcheck', 'docker-compose-config'],
  },
});

const remoteBranchOutput = runGit(['ls-remote', '--heads', 'origin', 'codex/latest-everywhere-local', 'main']);

check('GitHub-hosted CI boundary is explicit for the local no-push branch', {
  passed:
    remoteBranchOutput.includes('refs/heads/main') &&
    !remoteBranchOutput.includes('refs/heads/codex/latest-everywhere-local'),
  details: {
    command: 'git ls-remote --heads origin codex/latest-everywhere-local main',
    mainHeadPresent: remoteBranchOutput.includes('refs/heads/main'),
    localBranchPublished: remoteBranchOutput.includes('refs/heads/codex/latest-everywhere-local'),
  },
});

const failOpenWorkflows = workflowFiles.filter((workflow) => /continue-on-error:\s*true\b/i.test(workflow.text));

check('GitHub workflows do not enable continue-on-error true', {
  passed: failOpenWorkflows.length === 0,
  details: {
    workflowCount: workflowFiles.length,
    failOpenWorkflows: failOpenWorkflows.map((workflow) => workflow.path),
  },
});

check('actionlint validates GitHub workflows with a checksum-verified local binary', {
  passed:
    actionlintEvidence.includes('version=1.7.12') &&
    actionlintEvidence.includes('checksum_verified=true') &&
    actionlintEvidence.includes('command=.codex/tools/actionlint/actionlint.exe -color=false') &&
    actionlintEvidence.includes('exit_code=0') &&
    !actionlintEvidence.includes('[action]') &&
    !androidTvReleaseWorkflow.includes('softprops/action-gh-release@v1') &&
    androidTvReleaseWorkflow.includes('softprops/action-gh-release@v2'),
  details: {
    evidenceFile: '.codex/local-runtime/ac33-actionlint-20260708.txt',
    fixedWorkflow: '.github/workflows/android-tv-release.yml',
    fixedAction: 'softprops/action-gh-release@v2',
  },
});

check('CodeQL workflow fails closed on missing SARIF and high or critical findings', {
  passed:
    codeqlWorkflow.includes('languages: javascript-typescript') &&
    codeqlWorkflow.includes('languages: python') &&
    codeqlWorkflow.includes('output: sarif-results') &&
    codeqlWorkflow.includes('upload: true') &&
    codeqlWorkflow.includes('SARIF_FILE="sarif-results/javascript.sarif"') &&
    codeqlWorkflow.includes('SARIF_FILE="sarif-results/python.sarif"') &&
    codeqlWorkflow.includes('Expected CodeQL SARIF output is missing or empty') &&
    codeqlWorkflow.includes('security_severity') &&
    codeqlWorkflow.includes('>= 9.0') &&
    codeqlWorkflow.includes('>= 7.0') &&
    codeqlWorkflow.includes('Found $CRITICAL_COUNT critical and $HIGH_COUNT high severity security findings') &&
    codeqlWorkflow.includes('needs: [analyze-javascript, analyze-python]') &&
    codeqlWorkflow.includes('JS_RESULT') &&
    codeqlWorkflow.includes('PY_RESULT') &&
    codeqlWorkflow.includes('exit 1'),
  details: {
    evidenceFile: '.github/workflows/codeql.yml',
    expectedSarifFiles: ['sarif-results/javascript.sarif', 'sarif-results/python.sarif'],
  },
});

check('local CodeQL CLI evidence is recorded as supplementary high/critical-clean evidence', {
  passed:
    codeqlLocalSummary.status === 'partial' &&
    codeqlLocalSummary.hostedGitHubCodeql?.status === 'not_run' &&
    codeqlLocalSummary.codeqlCli?.version === '2.26.0' &&
    codeqlLocalSummary.codeqlCli?.checksumVerified === true &&
    codeqlLocalSummary.javascriptTypescript?.filesScanned === 1268 &&
    codeqlLocalSummary.javascriptTypescript?.result?.total === 0 &&
    codeqlLocalSummary.javascriptTypescript?.result?.highSeverityAtLeast7 === 0 &&
    codeqlLocalSummary.javascriptTypescript?.result?.criticalSeverityAtLeast9 === 0 &&
    codeqlLocalSummary.python?.filesScanned === 2307 &&
    codeqlLocalSummary.python?.result?.total === 90 &&
    codeqlLocalSummary.python?.result?.highSeverityAtLeast7 === 0 &&
    codeqlLocalSummary.python?.result?.criticalSeverityAtLeast9 === 0 &&
    codeqlLocalSummary.monitoringAvailability?.status === 'pass_by_user_context',
  details: {
    evidenceFile: '.codex/local-runtime/ac33-codeql-local-summary-20260708.json',
    jsFindings: codeqlLocalSummary.javascriptTypescript?.result ?? null,
    pythonFindings: codeqlLocalSummary.python?.result
      ? {
          total: codeqlLocalSummary.python.result.total,
          highSeverityAtLeast7: codeqlLocalSummary.python.result.highSeverityAtLeast7,
          criticalSeverityAtLeast9: codeqlLocalSummary.python.result.criticalSeverityAtLeast9,
        }
      : null,
    hostedGitHubCodeql: codeqlLocalSummary.hostedGitHubCodeql?.status ?? null,
  },
});

check('staging workflow boundary is explicit and not counted as a real deployment', {
  passed:
    deployStagingWorkflow.includes('workflow_dispatch') &&
    deployStagingWorkflow.includes('environment: staging') &&
    deployStagingWorkflow.includes('name: staging') &&
    deployStagingWorkflow.includes('Build and push backend image') &&
    deployStagingWorkflow.includes('Upload build artifacts') &&
    deployStagingWorkflow.includes('Configure deployment steps in this job once staging infrastructure is provisioned.') &&
    !deployStagingWorkflow.includes('production'),
  details: {
    evidenceFile: '.github/workflows/deploy-staging.yml',
    boundary: 'workflow is manually triggered and still contains a staging deploy placeholder, so it cannot prove real staging release/public smoke execution locally',
  },
});

check('stage1 deploy rehearsal is dry-run only', {
  passed:
    stage1DryRun.includes('Dry run: `true`') &&
    stage1DryRun.includes('No SSH, rsync, Docker build, compose restart or public smoke was executed.'),
  details: {
    evidenceFile: '.codex/local-runtime/ac33-stage1-dry-run/stage1-gitlab-deploy-local-ac33-20260707T164242Z.md',
  },
});

check('Ansible staging syntax rehearsal covers release and rollback playbooks', {
  passed:
    ansibleSyntax.includes('ansible-playbook [core 2.21.1]') &&
    [
      'playbooks/site.yml',
      'playbooks/remnawave-rollout.yml',
      'playbooks/rollback-remnawave.yml',
      'playbooks/helix-rollout.yml',
      'playbooks/rollback-helix.yml',
      'playbooks/alloy-rollout.yml',
      'playbooks/rollback-alloy.yml',
      'playbooks/control-plane-rollout.yml',
      'playbooks/rollback-control-plane.yml',
      'playbooks/control-plane-restore-drill.yml',
    ].every((playbook) => ansibleSyntax.includes(`syntax-check ${playbook}`) && ansibleSyntax.includes(`playbook: ${playbook}`)),
  details: {
    evidenceFile: '.codex/local-runtime/ac33-ansible-staging-syntax.txt',
  },
});

check('disposable repository rehearsal is idempotent', {
  passed: repoIdempotence.includes('changed=0') && repoIdempotence.includes('failed=0') && repoIdempotence.includes('exit 0'),
  details: {
    evidenceFile: '.codex/local-runtime/ac33-disposable-repo-idempotence.txt',
  },
});

check('disposable Alloy deploy verified service and metrics', {
  passed:
    alloyDeploy.includes('Assert service is running') &&
    alloyDeploy.includes('Assert metrics endpoint exposes Alloy telemetry') &&
    alloyDeploy.includes('failed=0'),
  details: {
    evidenceFile: '.codex/local-runtime/ac33-disposable-alloy-deploy-info.txt',
  },
});

check('disposable Alloy rollback restored a running monitored service', {
  passed:
    alloyRollback.includes('Restore previous config') &&
    alloyRollback.includes('Restart service after rollback') &&
    alloyRollback.includes('Assert metrics endpoint exposes Alloy telemetry') &&
    alloyRollback.includes('failed=0') &&
    alloyRollback.includes('exit 0') &&
    finalState.includes('Active: active (running)') &&
    finalState.includes('enabled') &&
    finalState.includes('alloy, version v1.17.1') &&
    finalState.includes('level  = "info"') &&
    finalState.includes('alloy_build_info'),
  details: {
    rollbackEvidenceFile: '.codex/local-runtime/ac33-disposable-alloy-rollback.txt',
    finalStateEvidenceFile: '.codex/local-runtime/ac33-disposable-final-state.txt',
  },
});

const failed = checks.filter((entry) => entry.status !== 'passed');
const output = {
  status: failed.length === 0 ? 'passed' : 'failed',
  checkCount: checks.length,
  passedCount: checks.length - failed.length,
  failedCount: failed.length,
  checkedAt: new Date().toISOString(),
  checks,
};

const outputPath = resolve(REPO_ROOT, OUTPUT_PATH);
mkdirSync(dirname(outputPath), { recursive: true });
writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`, 'utf8');
process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);

if (failed.length > 0) {
  process.exitCode = 1;
}

function check(name, { passed, details }) {
  checks.push({
    name,
    status: passed ? 'passed' : 'failed',
    details,
  });
}

function readJson(path) {
  return JSON.parse(readText(path));
}

function readText(path) {
  const fullPath = resolve(REPO_ROOT, path);
  if (!existsSync(fullPath)) {
    throw new Error(`Missing required evidence file: ${path}`);
  }
  return readFileSync(fullPath, 'utf8');
}

function readWorkflowFiles() {
  const workflowDir = resolve(REPO_ROOT, '.github', 'workflows');
  return readdirSync(workflowDir)
    .filter((filename) => filename.endsWith('.yml') || filename.endsWith('.yaml'))
    .sort()
    .map((filename) => {
      const path = `.github/workflows/${filename}`;
      return { path, text: readText(path) };
    });
}

function runGit(args) {
  return execFileSync('git', args, {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function includesAny(values, needles) {
  if (!Array.isArray(values)) {
    return false;
  }
  return values.some((value) => needles.some((needle) => String(value).includes(needle)));
}

function countBy(values, selector) {
  return values.reduce((counts, value) => {
    const key = selector(value);
    counts[key] = (counts[key] ?? 0) + 1;
    return counts;
  }, {});
}

function readCliOption(name) {
  const prefix = `--${name}=`;
  const inline = process.argv.find((arg) => arg.startsWith(prefix));
  if (inline) {
    return inline.slice(prefix.length);
  }
  const index = process.argv.indexOf(`--${name}`);
  if (index !== -1) {
    const value = process.argv[index + 1];
    if (!value || value.startsWith('--')) {
      throw new Error(`Missing value for --${name}.`);
    }
    return value;
  }
  return null;
}
