import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'],
    alias: {
      '@tanstack/react-query': resolve(__dirname, '../node_modules/@tanstack/react-query'),
      react: resolve(__dirname, '../node_modules/react'),
      'react-dom': resolve(__dirname, '../node_modules/react-dom'),
      'react-dom/client': resolve(__dirname, '../node_modules/react-dom/client.js'),
      'react/jsx-dev-runtime': resolve(__dirname, '../node_modules/react/jsx-dev-runtime.js'),
      'react/jsx-runtime': resolve(__dirname, '../node_modules/react/jsx-runtime.js'),
    },
  },
  test: {
    // Vitest supports both jsdom and happy-dom for browser-like tests.
    // We use happy-dom here because the current jsdom/cssstyle stack crashes
    // before test execution in this workspace runtime.
    pool: 'threads',
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
    alias: {
      '@': resolve(__dirname, './src'),
      'server-only': resolve(__dirname, './src/test/server-only.ts'),
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/test/**',
        'src/**/*.test.{ts,tsx}',
        'src/**/*.d.ts',
        'src/i18n/config.ts',
      ],
      thresholds: {
        statements: 50,
        branches: 40,
        functions: 40,
        lines: 50,
      },
    },
  },
});
