'use client';

import { RouteErrorBoundary } from '@/shared/ui/route-error-boundary';

export default function TestErrorPage() {
    // Mock error object to verify UI
    const mockError = new Error('This is a test error to verify the Error Boundary UI. It contains a long message to test the expand/collapse functionality and ensure that everything looks correct on different screen sizes.');
    (mockError as Error & { digest?: string }).digest = 'TEST_ERROR_123';
    mockError.stack = `Error: This is a test error
    at TestErrorPage (src/app/[locale]/test-error/page.tsx:5:21)
    at renderWithHooks (node_modules/react-dom/cjs/react-dom.development.js:16305:18)
    at mountIndeterminateComponent (node_modules/react-dom/cjs/react-dom.development.js:20074:13)
    at beginWork (node_modules/react-dom/cjs/react-dom.development.js:21587:16)
    at beginWork$1 (node_modules/react-dom/cjs/react-dom.development.js:27426:14)
    at performUnitOfWork (node_modules/react-dom/cjs/react-dom.development.js:26557:12)
    at workLoopSync (node_modules/react-dom/cjs/react-dom.development.js:26466:5)
    at renderRootSync (node_modules/react-dom/cjs/react-dom.development.js:26434:7)
    at recoverFromConcurrentError (node_modules/react-dom/cjs/react-dom.development.js:25850:20)
    at performSyncWorkOnRoot (node_modules/react-dom/cjs/react-dom.development.js:26096:20)`;

    return (
        <RouteErrorBoundary
            error={mockError as Error & { digest?: string }}
            reset={() => {
                // Simulate a reset action
                if (typeof window !== 'undefined') {
                    window.location.reload();
                }
            }}
        />
    );
}
