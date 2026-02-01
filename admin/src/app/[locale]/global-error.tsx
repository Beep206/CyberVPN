'use client';

import { useEffect } from 'react';

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('[GlobalError]', error);
    }, [error]);

    return (
        <html lang="en">
            <body
                style={{
                    margin: 0,
                    padding: 0,
                    backgroundColor: '#050505',
                    color: '#e0e0e0',
                    fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minHeight: '100vh',
                    textAlign: 'center',
                }}
            >
                <div style={{ maxWidth: '480px', padding: '2rem' }}>
                    <div
                        style={{
                            fontSize: '4rem',
                            color: '#ff00ff',
                            textShadow: '0 0 10px #ff00ff, 0 0 20px #ff00ff',
                            marginBottom: '1rem',
                        }}
                    >
                        FATAL ERROR
                    </div>

                    <p style={{ color: '#888', lineHeight: 1.6 }}>
                        A critical system failure has occurred. The root layout could not render.
                    </p>

                    {error.digest && (
                        <code
                            style={{
                                display: 'block',
                                marginTop: '1rem',
                                fontSize: '0.75rem',
                                color: 'rgba(0, 255, 255, 0.5)',
                            }}
                        >
                            DIGEST: {error.digest}
                        </code>
                    )}

                    <button
                        onClick={reset}
                        style={{
                            marginTop: '2rem',
                            padding: '0.75rem 2rem',
                            backgroundColor: 'transparent',
                            border: '1px solid #00ffff',
                            color: '#00ffff',
                            fontFamily: '"JetBrains Mono", monospace',
                            fontSize: '0.875rem',
                            cursor: 'pointer',
                            transition: 'background-color 0.2s',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.backgroundColor = 'rgba(0, 255, 255, 0.1)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                        aria-label="Retry operation"
                    >
                        RETRY OPERATION
                    </button>
                </div>
            </body>
        </html>
    );
}
