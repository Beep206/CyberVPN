'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';

interface CypherTextProps {
    text: string;
    className?: string;
    characters?: string;
    speed?: number; // ms per frame
    revealSpeed?: number; // ms to reveal next char
    trigger?: unknown; // Value that triggers replay when changed
    loop?: boolean; // NEW: infinite loop animation
    loopDelay?: number; // Delay between loops (ms)
}

const DEFAULT_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:",.<>?';

export function CypherText({
    text,
    className,
    characters = DEFAULT_CHARS,
    speed = 50,
    revealSpeed = 100,
    trigger,
    loop = false,
    loopDelay = 3000
}: CypherTextProps) {
    const [displayText, setDisplayText] = useState(text);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);
    const loopTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const animate = useCallback(() => {
        // Clear existing
        if (intervalRef.current) clearInterval(intervalRef.current);
        timeoutsRef.current.forEach(clearTimeout);
        timeoutsRef.current = [];
        if (loopTimeoutRef.current) clearTimeout(loopTimeoutRef.current);

        const textChars = text.split('');
        const charsLength = characters.length;
        let revealIndex = 0;

        // Scramble interval
        intervalRef.current = setInterval(() => {
            const result = new Array(textChars.length);
            for (let i = 0; i < textChars.length; i++) {
                if (i < revealIndex) {
                    result[i] = textChars[i];
                } else if (textChars[i] === ' ') {
                    result[i] = ' ';
                } else {
                    result[i] = characters[Math.floor(Math.random() * charsLength)];
                }
            }
            setDisplayText(result.join(''));
        }, speed);

        // Schedule reveals
        for (let i = 0; i <= text.length; i++) {
            const timeout = setTimeout(() => {
                revealIndex = i;
                if (i === text.length && intervalRef.current) {
                    clearInterval(intervalRef.current);
                    setDisplayText(text); // Ensure final state is clean

                    // If loop is enabled, restart after delay
                    if (loop) {
                        loopTimeoutRef.current = setTimeout(() => {
                            animate();
                        }, loopDelay);
                    }
                }
            }, i * revealSpeed);
            timeoutsRef.current.push(timeout);
        }
    }, [text, characters, speed, revealSpeed, loop, loopDelay]);

    useEffect(() => {
        animate();
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
            timeoutsRef.current.forEach(clearTimeout);
            if (loopTimeoutRef.current) clearTimeout(loopTimeoutRef.current);
        };
    }, [animate, trigger]);

    return (
        <span
            aria-label={text}
            className={cn("font-mono inline-block", className)}
            onMouseEnter={animate} // Replay on hover
        >
            <span aria-hidden="true">{displayText}</span>
        </span>
    );
}

