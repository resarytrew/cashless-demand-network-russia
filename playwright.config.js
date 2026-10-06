const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests/browser',
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:8765', headless: true, reducedMotion: 'reduce', ...(process.env.PLAYWRIGHT_CHANNEL ? { channel:process.env.PLAYWRIGHT_CHANNEL } : {}) },
  webServer: { command: 'python -m http.server 8765 --bind 127.0.0.1 --directory dist', url: 'http://127.0.0.1:8765', reuseExistingServer: !process.env.CI },
  projects: [{ name:'chromium', use: { browserName: 'chromium' } }],
});
