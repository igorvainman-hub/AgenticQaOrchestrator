import { defineConfig } from '@playwright/test';
import { execSync } from 'child_process';

const baseURL = (() => {
  try {
    return execSync('node scripts/extract_base_url.js', { encoding: 'utf8' }).trim();
  } catch {
    return 'http://localhost:3000';
  }
})();

export default defineConfig({
  use: { baseURL },
  reporter: [['html'], ['list']],
  timeout: 30000,
});