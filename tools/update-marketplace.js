#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, '../package.json'), 'utf8'));
const pluginName = pkg.name.replace(/^@[^/]+\//, '');
const newVersion = pkg.version;

const marketplacePath = path.join(__dirname, '../../marketplace/.claude-plugin/marketplace.json');

if (!fs.existsSync(marketplacePath)) {
  console.log(`Marketplace not found at ${marketplacePath} — skipping`);
  process.exit(0);
}

const data = JSON.parse(fs.readFileSync(marketplacePath, 'utf8'));
const plugin = data.plugins.find(p => p.name === pluginName);

if (!plugin) {
  console.log(`Plugin "${pluginName}" not found in marketplace.json — skipping`);
  process.exit(0);
}

const oldVersion = plugin.version;
plugin.version = newVersion;
fs.writeFileSync(marketplacePath, JSON.stringify(data, null, 2) + '\n');
console.log(`Updated ${pluginName}: ${oldVersion} → ${newVersion}`);

const marketplaceDir = path.dirname(path.dirname(marketplacePath));
execSync(`git add .claude-plugin/marketplace.json`, { cwd: marketplaceDir, stdio: 'inherit' });
execSync(`git commit -m "chore: update ${pluginName} to v${newVersion}"`, { cwd: marketplaceDir, stdio: 'inherit' });
execSync(`git push`, { cwd: marketplaceDir, stdio: 'inherit' });
console.log('Marketplace updated and pushed.');
