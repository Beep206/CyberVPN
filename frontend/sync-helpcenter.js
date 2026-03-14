const fs = require('fs');
const path = require('path');

const localesDir = path.join(__dirname, 'messages');
const baseFile = path.join(localesDir, 'en-EN', 'HelpCenter.json');
const baseContent = fs.readFileSync(baseFile, 'utf8');

const dirs = fs.readdirSync(localesDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory() && dirent.name !== 'en-EN' && dirent.name !== 'ru-RU')
    .map(dirent => dirent.name);

for (const dir of dirs) {
    const destFile = path.join(localesDir, dir, 'HelpCenter.json');
    fs.writeFileSync(destFile, baseContent, 'utf8');
}
console.log('Copied HelpCenter.json to all locales successfully.');
