'use client';

import * as Sentry from '@sentry/nextjs';
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
    /** Optional custom fallback. If omitted, a default cyberpunk-styled fallback renders. */
    fallback?: ReactNode;
    /** Label shown in the fallback to identify which widget crashed. */
    label?: string;
}

interface State {
    hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(): State {
        return { hasError: true };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } });
    }

    private handleRetry = () => {
        this.setState({ hasError: false });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div
                    style={{
                        padding: '1.5rem',
                        fontFamily: "'JetBrains Mono', monospace",
                        background: 'rgba(10, 10, 10, 0.85)',
                        border: '1px solid #ff00ff',
                        borderRadius: '4px',
                        color: '#00ffff',
                        textAlign: 'center',
                    }}
                >
                    <p style={{ margin: '0 0 0.75rem', fontSize: '0.85rem', opacity: 0.8 }}>
                        {this.props.label ? `[${this.props.label}] ` : ''}Component error
                    </p>
                    <button
                        onClick={this.handleRetry}
                        aria-label="Retry loading component"
                        style={{
                            padding: '0.4rem 1rem',
                            background: '#ff00ff',
                            color: '#000',
                            border: 'none',
                            cursor: 'pointer',
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: '0.8rem',
                            borderRadius: '2px',
                        }}
                    >
                        RETRY
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}
