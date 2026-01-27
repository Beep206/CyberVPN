'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

interface CypherTextProps {
    text: string;
    className?: string;
    characters?: string;
    speed?: number; // ms per frame
    revealSpeed?: number; // ms to reveal next char
    trigger?: any; // Value that triggers replay when changed
}

const DEFAULT_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:",./<>?';

export function CypherText({
    text,
    className,
    characters = DEFAULT_CHARS,
    speed = 50,
    revealSpeed = 100,
    trigger
}: CypherTextProps) {
    const [displayText, setDisplayText] = useState(text);
    const intervalRef = useRef<NodeJS.Timeout>(null);
    const timeoutsRef = useRef<NodeJS.Timeout[]>([]);

    const animate = () => {
        // Clear existing
        if (intervalRef.current) clearInterval(intervalRef.current);
        timeoutsRef.current.forEach(clearTimeout);
        timeoutsRef.current = [];

        let revealIndex = 0;

        // Scramble interval
        intervalRef.current = setInterval(() => {
            setDisplayText(prev => {
                return text
                    .split('')
                    .map((char, i) => {
                        if (i < revealIndex) return text[i];
                        if (char === ' ') return ' ';
                        return characters[Math.floor(Math.random() * characters.length)];
                    })
                    .join('');
            });
        }, speed);

        // Reveal sequence
        const totalTime = text.length * revealSpeed;

        // Schedule reveals
        for (let i = 0; i <= text.length; i++) {
            const timeout = setTimeout(() => {
                revealIndex = i;
                if (i === text.length && intervalRef.current) {
                    clearInterval(intervalRef.current);
                    setDisplayText(text); // Ensure final state is clean
                }
            }, i * revealSpeed);
            timeoutsRef.current.push(timeout);
        }
    };

    useEffect(() => {
        animate();
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
            timeoutsRef.current.forEach(clearTimeout);
        };
    }, [text, trigger]);

    return (
        <span
            className={cn("font-mono inline-block", className)}
            onMouseEnter={() => animate()} // Replay on hover
        >
            {displayText}
        </span>
    );
}
