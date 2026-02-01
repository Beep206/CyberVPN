#!/usr/bin/env node

/**
 * Generate app icon PNG files from SVG
 * Uses sharp from the admin workspace
 */

import { readFile } from 'fs/promises';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

async function main() {
  try {
    // Import sharp from admin workspace
    const sharpModule = await import(join(projectRoot, '..', 'admin', 'node_modules', 'sharp', 'lib', 'index.js'));
    const sharp = sharpModule.default;

    console.log('Converting SVG icons to PNG...\n');

    // Convert main icon
    const mainIconSvg = await readFile(join(projectRoot, 'assets', 'images', 'app_icon.svg'));
    await sharp(mainIconSvg)
      .resize(1024, 1024)
      .png()
      .toFile(join(projectRoot, 'assets', 'images', 'app_icon.png'));
    console.log('✓ Created app_icon.png (1024x1024)');

    // Convert foreground layer
    const foregroundSvg = await readFile(join(projectRoot, 'assets', 'images', 'app_icon_foreground.svg'));
    await sharp(foregroundSvg)
      .resize(1024, 1024)
      .png()
      .toFile(join(projectRoot, 'assets', 'images', 'app_icon_foreground.png'));
    console.log('✓ Created app_icon_foreground.png (1024x1024)');

    console.log('\n✅ Icon generation complete!');
  } catch (error) {
    console.error('Error generating icons:', error.message);
    console.error('\nPlease ensure sharp is installed:');
    console.error('  cd ../admin && npm install');
    process.exit(1);
  }
}

main();
