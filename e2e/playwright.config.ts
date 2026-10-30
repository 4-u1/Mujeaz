import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  timeout: 60_000,
  retries: 1,
  reporter: 'line',
  use: { baseURL: process.env.MUJEAZ_E2E_URL || 'http://localhost:8080', locale: 'en-US' },
});
