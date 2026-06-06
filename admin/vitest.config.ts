import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { existsSync } from 'fs';
import { resolve } from 'path';

const resolveWorkspaceDependency = (...segments: string[]) => {
  const localPath = resolve(__dirname, 'node_modules', ...segments);
  if (existsSync(localPath)) {
    return localPath;
  }

  return resolve(__dirname, '..', 'node_modules', ...segments);
};

const browserTestDeps = [
  '@tanstack/react-query',
  '@testing-library/dom',
  '@testing-library/jest-dom/vitest',
  '@testing-library/react',
  '@testing-library/user-event',
];

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'],
    alias: {
      '@tanstack/react-query': resolveWorkspaceDependency('@tanstack/react-query'),
      react: resolveWorkspaceDependency('react'),
      'react-dom': resolveWorkspaceDependency('react-dom'),
      'react-dom/client': resolveWorkspaceDependency('react-dom/client.js'),
      'react/jsx-dev-runtime': resolveWorkspaceDependency('react/jsx-dev-runtime.js'),
      'react/jsx-runtime': resolveWorkspaceDependency('react/jsx-runtime.js'),
    },
  },
  test: {
    // Match the frontend runner: the current jsdom/cssstyle stack crashes
    // before test execution in this workspace runtime.
    pool: 'threads',
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
    deps: {
      optimizer: {
        client: {
          enabled: true,
          include: browserTestDeps,
        },
      },
    },
    alias: {
      '@': resolve(__dirname, './src'),
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
