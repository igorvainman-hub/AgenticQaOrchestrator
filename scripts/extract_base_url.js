const fs = require('fs');

const filePath = process.env.FEATURE_FILE || 'new_feature.txt';

let content = '';
try {
  content = fs.readFileSync(filePath, 'utf8');
} catch {
  console.log('http://localhost:3000');
  process.exit(0);
}

const baseUrlMatch = content.match(/Base URL:\s*(https?:\/\/\S+)/i);
if (baseUrlMatch) {
  console.log(baseUrlMatch[1].replace(/[.,;)]+$/, ''));
  process.exit(0);
}

const genericMatch = content.match(/(https?:\/\/[^\s]+)/);
if (genericMatch) {
  console.log(genericMatch[1].replace(/[.,;)]+$/, ''));
  process.exit(0);
}

console.log('http://localhost:3000');