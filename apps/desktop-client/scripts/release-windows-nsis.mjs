import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appDir = path.resolve(__dirname, "..");
const packageJsonPath = path.join(appDir, "package.json");
const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf8"));

const target = process.env.DESKTOP_TAURI_TARGET ?? "x86_64-pc-windows-msvc";
const runner = process.env.DESKTOP_TAURI_RUNNER ?? "cargo-xwin";
const skipVerify = process.env.DESKTOP_RELEASE_SKIP_VERIFY === "1";
const signRelease = process.env.DESKTOP_RELEASE_SIGN === "1";

function runCommand(command, args) {
  const rendered = [command, ...args].join(" ");
  console.log(`\n> ${rendered}`);

  const result = spawnSync(command, args, {
    cwd: appDir,
    stdio: "inherit",
    env: process.env,
  });

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function runCapture(command, args) {
  const result = spawnSync(command, args, {
    cwd: appDir,
    stdio: ["ignore", "pipe", "pipe"],
    env: process.env,
    encoding: "utf8",
  });

  if (result.status !== 0) {
    return null;
  }

  return result.stdout.trim();
}

function resolveWindowsArch(targetTriple) {
  if (targetTriple.startsWith("x86_64-")) {
    return "x64";
  }

  if (targetTriple.startsWith("aarch64-")) {
    return "arm64";
  }

  if (targetTriple.startsWith("i686-")) {
    return "x86";
  }

  return "x64";
}

function resolveInstallerPath(version, arch) {
  const bundleDir = path.join(
    appDir,
    "src-tauri",
    "target",
    target,
    "release",
    "bundle",
    "nsis",
  );
  const expectedName = `${packageJson.name}_${version}_${arch}-setup.exe`;
  const expectedPath = path.join(bundleDir, expectedName);

  if (existsSync(expectedPath)) {
    return expectedPath;
  }

  const fallback = readdirSync(bundleDir).find(
    (entry) => entry.endsWith("-setup.exe") && entry.includes(version),
  );

  if (!fallback) {
    throw new Error(`Unable to locate NSIS installer in ${bundleDir}.`);
  }

  return path.join(bundleDir, fallback);
}

function createReleaseNotes({
  productName,
  version,
  target,
  arch,
  runner,
  signed,
  verifyChecksRan,
  installerName,
  checksumFileName,
  manifestFileName,
  checksumsFileName,
  createdAt,
  branch,
  commit,
}) {
  const notes = [
    `${productName} ${version}`,
    "Windows NSIS Release",
    "",
    `Generated: ${createdAt}`,
    `Target: ${target}`,
    `Architecture: ${arch}`,
    `Runner: ${runner}`,
    `Host platform: ${process.platform}`,
    `Branch: ${branch ?? "unknown"}`,
    `Commit: ${commit ?? "unknown"}`,
    "",
    "Verification",
    `- Tests: ${verifyChecksRan ? "passed" : "skipped"}`,
    `- npm audit --omit=dev: ${verifyChecksRan ? "passed" : "skipped"}`,
    `- Signing: ${signed ? "enabled" : "skipped"}`,
    "",
    "Artifacts",
    `- ${installerName}`,
    `- ${checksumFileName}`,
    `- ${manifestFileName}`,
    `- ${checksumsFileName}`,
    "- release-notes.txt",
    "",
    "GitHub Release Upload Order",
    `1. ${installerName}`,
    `2. ${checksumFileName}`,
    `3. ${manifestFileName}`,
    `4. ${checksumsFileName}`,
    "5. release-notes.txt",
    "",
    "Notes",
    "- This release bundle is ready to upload to a GitHub release as-is.",
  ];

  if (process.platform !== "win32") {
    notes.push("- Built on a non-Windows host via cross-compilation.");
    notes.push("- Tauri cross-build and NSIS host warnings are expected in this environment.");
  }

  if (!signed) {
    notes.push("- Windows code signing was skipped for this build.");
  }

  return `${notes.join("\n")}\n`;
}

if (!skipVerify) {
  runCommand("npm", ["run", "test"]);
  runCommand("npm", ["audit", "--omit=dev"]);
}

const buildArgs = ["run", "tauri", "build", "--", "--runner", runner, "--target", target];
if (!signRelease) {
  buildArgs.push("--no-sign");
}

runCommand("npm", buildArgs);

const version = packageJson.version;
const arch = resolveWindowsArch(target);
const installerPath = resolveInstallerPath(version, arch);
const installerName = path.basename(installerPath);
const installerBytes = readFileSync(installerPath);
const sha256 = createHash("sha256").update(installerBytes).digest("hex");
const checksumPath = `${installerPath}.sha256`;
const manifestPath = `${installerPath}.release.json`;
const createdAt = new Date().toISOString();
const branch = runCapture("git", ["branch", "--show-current"]);
const commit = runCapture("git", ["rev-parse", "--short", "HEAD"]);
const releaseDir = path.join(appDir, "releases", "windows-nsis", `${packageJson.name}_${version}_${arch}`);
const checksumsPath = path.join(releaseDir, "SHA256SUMS.txt");
const releaseNotesPath = path.join(releaseDir, "release-notes.txt");
const bundledInstallerPath = path.join(releaseDir, installerName);
const checksumFileName = path.basename(checksumPath);
const manifestFileName = path.basename(manifestPath);
const checksumsFileName = path.basename(checksumsPath);

writeFileSync(checksumPath, `${sha256}  ${installerName}\n`, "utf8");
rmSync(releaseDir, { recursive: true, force: true });
mkdirSync(releaseDir, { recursive: true });
copyFileSync(installerPath, bundledInstallerPath);
copyFileSync(checksumPath, path.join(releaseDir, checksumFileName));
writeFileSync(
  manifestPath,
  JSON.stringify(
    {
      productName: packageJson.name,
      version,
      target,
      arch,
      runner,
      signed: signRelease,
      verifyChecksRan: !skipVerify,
      createdAt,
      branch,
      commit,
      installerName,
      installerPath,
      sha256,
      checksumPath,
      releaseBundleDir: releaseDir,
      githubReleaseFiles: [
        installerName,
        checksumFileName,
        manifestFileName,
        checksumsFileName,
        "release-notes.txt",
      ],
    },
    null,
    2,
  ),
  "utf8",
);
copyFileSync(manifestPath, path.join(releaseDir, manifestFileName));
writeFileSync(checksumsPath, `${sha256}  ${installerName}\n`, "utf8");
writeFileSync(
  releaseNotesPath,
  createReleaseNotes({
    productName: packageJson.name,
    version,
    target,
    arch,
    runner,
    signed: signRelease,
    verifyChecksRan: !skipVerify,
    installerName,
    checksumFileName,
    manifestFileName,
    checksumsFileName,
    createdAt,
    branch,
    commit,
  }),
  "utf8",
);

console.log("\nRelease artifacts ready:");
console.log(`- Installer: ${installerPath}`);
console.log(`- SHA-256: ${sha256}`);
console.log(`- Checksum file: ${checksumPath}`);
console.log(`- Manifest: ${manifestPath}`);
console.log(`- GitHub release bundle: ${releaseDir}`);
