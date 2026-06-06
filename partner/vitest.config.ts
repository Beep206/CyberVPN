import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { existsSync } from 'fs';
import { resolve } from 'path';

const partnerNodeModules = resolve(__dirname, './node_modules');
const partnerSrc = resolve(__dirname, './src');

const resolveWorkspaceDependency = (...segments: string[]) => {
  const localPath = resolve(partnerNodeModules, ...segments);
  if (existsSync(localPath)) {
    return localPath;
  }

  return resolve(__dirname, '..', 'node_modules', ...segments);
};

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': partnerSrc,
      '@testing-library/react': resolve(partnerSrc, 'test/react-testing-library.ts'),
      react: resolveWorkspaceDependency('react'),
      'react/jsx-runtime': resolveWorkspaceDependency('react/jsx-runtime.js'),
      'react/jsx-dev-runtime': resolveWorkspaceDependency('react/jsx-dev-runtime.js'),
      'react-dom': resolveWorkspaceDependency('react-dom'),
      'react-dom/client': resolveWorkspaceDependency('react-dom/client.js'),
      'react-dom/test-utils': resolveWorkspaceDependency('react-dom/test-utils.js'),
    },
    dedupe: ['react', 'react-dom'],
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
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
