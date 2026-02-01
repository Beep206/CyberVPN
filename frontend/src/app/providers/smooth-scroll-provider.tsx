'use client';

import { ReactNode, useEffect, useRef } from 'react';
import Lenis from 'lenis';

export function SmoothScrollProvider({ children }: { children: ReactNode }) {
    const lenisRef = useRef<Lenis | null>(null);

    useEffect(() => {
        const lenis = new Lenis({
            duration: 1.2,
            easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)), // Exponential easing
            orientation: 'vertical',
            gestureOrientation: 'vertical',
            smoothWheel: true,
            wheelMultiplier: 1,
            touchMultiplier: 2,
            autoRaf: true,
        });

        lenisRef.current = lenis;

        const stopLenis = () => lenis.stop();
        const startLenis = () => lenis.start();

        window.addEventListener('lenis:stop', stopLenis);
        window.addEventListener('lenis:start', startLenis);

        return () => {
            window.removeEventListener('lenis:stop', stopLenis);
            window.removeEventListener('lenis:start', startLenis);
            lenis.destroy();
        };
    }, []);

    return <div className="no-scrollbar">{children}</div>;
}
