#!/usr/bin/env node

/**
 * Convert SVG app icons to PNG format for Flutter app
 * This script uses sharp package which supports SVG rendering
 */

import { readFile, writeFile } from 'fs/promises';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');
const assetsPath = join(projectRoot, 'assets', 'images');

async function convertSvgToPng(svgPath, pngPath, width = 1024, height = 1024) {
  try {
    // Try to use sharp if available
    const sharp = await import('sharp').catch(() => null);

    if (sharp) {
      const svgBuffer = await readFile(svgPath);
      await sharp.default(svgBuffer)
        .resize(width, height)
        .png()
        .toFile(pngPath);
      console.log(`✓ Converted ${svgPath} to ${pngPath} using sharp`);
      return true;
    }
  } catch (error) {
    console.error(`Error with sharp conversion: ${error.message}`);
  }

  return false;
}

async function main() {
  console.log('Converting app icon SVG files to PNG...\n');

  const conversions = [
    {
      svg: join(assetsPath, 'app_icon.svg'),
      png: join(assetsPath, 'app_icon.png'),
      name: 'Main app icon'
    },
    {
      svg: join(assetsPath, 'app_icon_foreground.svg'),
      png: join(assetsPath, 'app_icon_foreground.png'),
      name: 'Foreground layer'
    }
  ];

  let successCount = 0;
  const errors = [];

  for (const { svg, png, name } of conversions) {
    console.log(`Converting ${name}...`);
    const success = await convertSvgToPng(svg, png);
    if (success) {
      successCount++;
    } else {
      errors.push(name);
    }
  }

  console.log(`\n${successCount}/${conversions.length} conversions completed`);

  if (errors.length > 0) {
    console.error('\nFailed conversions:', errors.join(', '));
    console.error('\nTo install sharp: cd cybervpn_mobile && npm install sharp');
    process.exit(1);
  }

  console.log('\n✓ All icons converted successfully!');
}

main().catch(error => {
  console.error('Conversion failed:', error);
  process.exit(1);
});
