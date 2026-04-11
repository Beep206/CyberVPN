import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const localesDir = path.join(__dirname, 'messages');
const baseFile = path.join(localesDir, 'en-EN', 'Docs.json');
const baseContent = fs.readFileSync(baseFile, 'utf8');

const dirs = fs.readdirSync(localesDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory() && dirent.name !== 'en-EN' && dirent.name !== 'ru-RU')
    .map(dirent => dirent.name);

for (const dir of dirs) {
    const destFile = path.join(localesDir, dir, 'Docs.json');
    fs.writeFileSync(destFile, baseContent, 'utf8');
}
process.stdout.write('Copied Docs.json to all locales successfully.\n');
