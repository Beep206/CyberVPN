'use client';

import dynamic from "next/dynamic";
import { Component, ErrorInfo, ReactNode } from "react";

const GlobalNetworkScene = dynamic(() => import("@/3d/scenes/GlobalNetwork"), {
    ssr: false,
});

class ErrorBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { hasError: boolean }> {
    constructor(props: { children: ReactNode; fallback: ReactNode }) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError() {
        return { hasError: true };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("3D Scene Error:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return this.props.fallback;
        }
        return this.props.children;
    }
}

export function GlobalNetworkWrapper() {
    return (
        <ErrorBoundary fallback={<div className="w-full h-full bg-terminal-bg" />}>
            <GlobalNetworkScene />
        </ErrorBoundary>
    );
}
