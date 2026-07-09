#!/usr/bin/env node

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { cwd, exit } from 'node:process';

const WORKSPACES = ['frontend', 'admin', 'partner'];
const DEPENDENCY_SECTIONS = ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'];
const EXACT_VERSION = /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/;

function readPackageJson(workspace) {
  const manifestPath = join(cwd(), workspace, 'package.json');
  return JSON.parse(readFileSync(manifestPath, 'utf8'));
}

function collectDirectDependencies() {
  const dependenciesByName = new Map();
  const exactVersionErrors = [];

  for (const workspace of WORKSPACES) {
    const manifest = readPackageJson(workspace);

    for (const section of DEPENDENCY_SECTIONS) {
      const dependencies = manifest[section] ?? {};

      for (const [name, version] of Object.entries(dependencies)) {
        if (!EXACT_VERSION.test(version)) {
          exactVersionErrors.push(`${workspace}:${section}:${name} uses non-exact version "${version}"`);
        }

        if (!dependenciesByName.has(name)) {
          dependenciesByName.set(name, []);
        }

        dependenciesByName.get(name).push({
          workspace,
          section,
          version,
        });
      }
    }
  }

  return { dependenciesByName, exactVersionErrors };
}

function findDrift(dependenciesByName) {
  const driftErrors = [];

  for (const [name, entries] of dependenciesByName.entries()) {
    const participatingWorkspaces = new Set(entries.map((entry) => entry.workspace));

    if (participatingWorkspaces.size < 2) {
      continue;
    }

    const versions = new Map();
    for (const entry of entries) {
      if (!versions.has(entry.version)) {
        versions.set(entry.version, []);
      }
      versions.get(entry.version).push(`${entry.workspace}:${entry.section}`);
    }

    if (versions.size > 1) {
      const detail = [...versions.entries()]
        .map(([version, owners]) => `${version} at ${owners.join(', ')}`)
        .join('; ');
      driftErrors.push(`${name} has divergent versions: ${detail}`);
    }
  }

  return driftErrors;
}

const { dependenciesByName, exactVersionErrors } = collectDirectDependencies();
const driftErrors = findDrift(dependenciesByName);
const errors = [...exactVersionErrors, ...driftErrors];

if (errors.length > 0) {
  console.error('Web workspace dependency drift detected:');
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  exit(1);
}

console.log('Web workspace dependency versions are exact and aligned across frontend/admin/partner.');
