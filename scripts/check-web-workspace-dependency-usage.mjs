#!/usr/bin/env node

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { cwd, exit } from 'node:process';

const WORKSPACES = ['frontend', 'admin', 'partner'];
const DEPENDENCY_SECTIONS = ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'];
const SOURCE_EXTENSIONS = new Set([
  '.cjs',
  '.css',
  '.cts',
  '.js',
  '.jsx',
  '.mjs',
  '.mts',
  '.scss',
  '.ts',
  '.tsx',
]);

const SKIPPED_DIRECTORIES = new Set([
  '.next',
  '.turbo',
  '.vercel',
  'build',
  'coverage',
  'dist',
  'node_modules',
  'out',
]);

const CONFIG_LITERAL_PACKAGES = new Set([
  '@tailwindcss/postcss',
  '@testing-library/dom',
  'happy-dom',
]);

const SCRIPT_CLI_PACKAGES = new Map([
  ['eslint', ['eslint']],
  ['next', ['next']],
  ['vitest', ['vitest']],
]);

const TOOLING_OWNERS = new Map([
  ['@types/node', 'Node ambient types for Next/Vitest/config scripts.'],
  ['@types/qrcode', 'Type declarations for the qrcode runtime package.'],
  ['@types/react', 'React ambient types for TSX compilation.'],
  ['@types/react-dom', 'React DOM ambient types for TSX compilation.'],
  ['@vitest/coverage-v8', 'Vitest coverage provider loaded by vitest run --coverage.'],
  ['babel-plugin-react-compiler', 'React Compiler peer used when next.config.ts enables reactCompiler.'],
  ['openapi-typescript', 'Generated API client CLI used by scripts/generate-api-types.mjs.'],
  ['postcss', 'PostCSS peer for Tailwind 4 and the Next CSS pipeline.'],
  ['typescript', 'TypeScript compiler used by the required npm exec tsc --noEmit gate.'],
  ['vite', 'Vite peer for Vitest and @vitejs/plugin-react test configuration.'],
]);

const IMPORT_PATTERNS = [
  /\bfrom\s*["']([^"']+)["']/g,
  /\bimport\s*["']([^"']+)["']/g,
  /\bimport\s*\(\s*["']([^"']+)["']\s*\)/g,
  /\brequire\s*\(\s*["']([^"']+)["']\s*\)/g,
  /@import\s*["']([^"']+)["']/g,
];

function readPackageJson(workspace) {
  return JSON.parse(readFileSync(join(cwd(), workspace, 'package.json'), 'utf8'));
}

function packageRoot(specifier) {
  if (specifier.startsWith('@')) {
    const [scope, name] = specifier.split('/');
    return scope && name ? `${scope}/${name}` : specifier;
  }

  return specifier.split('/')[0] ?? specifier;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function isSourceFile(fileName) {
  if (
    fileName === 'package.json' ||
    fileName === 'package-lock.json' ||
    fileName.endsWith('.tsbuildinfo') ||
    /^eslint-report.*\.json$/u.test(fileName)
  ) {
    return false;
  }

  const extension = fileName.slice(fileName.lastIndexOf('.'));
  return SOURCE_EXTENSIONS.has(extension);
}

function collectFiles(directory) {
  const files = [];

  for (const entry of readdirSync(directory)) {
    const absolutePath = join(directory, entry);
    const entryStat = statSync(absolutePath);

    if (entryStat.isDirectory()) {
      if (SKIPPED_DIRECTORIES.has(entry) || entry.startsWith('.next-')) {
        continue;
      }

      files.push(...collectFiles(absolutePath));
      continue;
    }

    if (entryStat.isFile() && isSourceFile(entry)) {
      files.push(absolutePath);
    }
  }

  return files;
}

function collectDirectDependencies(manifest) {
  const dependencies = new Map();

  for (const section of DEPENDENCY_SECTIONS) {
    for (const name of Object.keys(manifest[section] ?? {})) {
      dependencies.set(name, section);
    }
  }

  return dependencies;
}

function collectImportSpecifiers(source) {
  const specifiers = new Set();

  for (const pattern of IMPORT_PATTERNS) {
    pattern.lastIndex = 0;
    for (const match of source.matchAll(pattern)) {
      if (match[1]) {
        specifiers.add(match[1]);
      }
    }
  }

  return specifiers;
}

function scriptUsesPackage(scripts, packageName) {
  const commands = SCRIPT_CLI_PACKAGES.get(packageName);
  if (!commands) {
    return false;
  }

  return Object.values(scripts ?? {}).some((script) =>
    commands.some((command) => new RegExp(`(^|[\\s;&|])${escapeRegExp(command)}([\\s]|$)`, 'u').test(script)),
  );
}

function hasToolingOwner(packageName, workspace, usageByPackage) {
  const reason = TOOLING_OWNERS.get(packageName);
  if (!reason) {
    return null;
  }

  if (packageName === '@types/qrcode' && !usageByPackage.has('qrcode')) {
    return null;
  }

  if (packageName === 'babel-plugin-react-compiler') {
    const configPath = join(cwd(), workspace, 'next.config.ts');
    if (!existsSync(configPath) || !readFileSync(configPath, 'utf8').includes('reactCompiler: true')) {
      return null;
    }
  }

  return reason;
}

function collectWorkspaceUsage(workspace, directDependencies, scripts) {
  const usageByPackage = new Map();
  const files = collectFiles(join(cwd(), workspace));

  for (const [packageName] of directDependencies) {
    if (scriptUsesPackage(scripts, packageName)) {
      usageByPackage.set(packageName, [`package.json:scripts uses ${packageName}`]);
    }
  }

  for (const file of files) {
    const source = readFileSync(file, 'utf8');
    const relativePath = relative(cwd(), file);
    const specifiers = collectImportSpecifiers(source);

    for (const specifier of specifiers) {
      const root = packageRoot(specifier);
      if (!directDependencies.has(root)) {
        continue;
      }

      if (!usageByPackage.has(root)) {
        usageByPackage.set(root, []);
      }
      usageByPackage.get(root).push(`${relativePath} imports ${specifier}`);
    }

    for (const packageName of CONFIG_LITERAL_PACKAGES) {
      if (!directDependencies.has(packageName)) {
        continue;
      }

      const quotedPackage = new RegExp(`["']${escapeRegExp(packageName)}["']`, 'u');
      if (!quotedPackage.test(source)) {
        continue;
      }

      if (!usageByPackage.has(packageName)) {
        usageByPackage.set(packageName, []);
      }
      usageByPackage.get(packageName).push(`${relativePath} configures ${packageName}`);
    }
  }

  return usageByPackage;
}

const errors = [];
const ownerNotes = [];

for (const workspace of WORKSPACES) {
  const manifest = readPackageJson(workspace);
  const directDependencies = collectDirectDependencies(manifest);
  const usageByPackage = collectWorkspaceUsage(workspace, directDependencies, manifest.scripts);

  for (const [packageName, section] of directDependencies) {
    if (usageByPackage.has(packageName)) {
      continue;
    }

    const ownerReason = hasToolingOwner(packageName, workspace, usageByPackage);
    if (ownerReason) {
      ownerNotes.push(`${workspace}:${section}:${packageName} retained: ${ownerReason}`);
      continue;
    }

    errors.push(`${workspace}:${section}:${packageName} has no source/config/script/tooling owner`);
  }
}

if (errors.length > 0) {
  console.error('Web workspace dependencies without ownership evidence:');
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  exit(1);
}

console.log('Web workspace direct dependencies have source, config, script, or documented tooling owners.');
if (ownerNotes.length > 0) {
  console.log('Documented tooling owners:');
  for (const note of ownerNotes) {
    console.log(`- ${note}`);
  }
}
