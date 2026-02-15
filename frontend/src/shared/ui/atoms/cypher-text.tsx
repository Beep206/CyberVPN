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
    delay?: number; // Initial delay before starting animation (ms)
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
    loopDelay = 3000,
    delay = 0
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
        let timeoutId: NodeJS.Timeout;

        if (trigger !== undefined) {
            if (delay > 0) {
                timeoutId = setTimeout(animate, delay);
            } else {
                animate();
            }
        } else {
            // If no trigger (run on mount), also respect delay
            if (delay > 0) {
                // Initially show full text or empty? 
                // Standard behavior: show text, then scramble. 
                // Or scramble from start?
                // Let's assume we want to start animation after delay.
                setDisplayText(text); // Reset first
                timeoutId = setTimeout(animate, delay);
            } else {
                setDisplayText(text);
                // Note: Original code didn't auto-animate on mount if trigger was undefined, 
                // it just set text. Keeping that behavior unless we want auto-play.
                // Looking at lines 83-85: 
                // } else { setDisplayText(text); }
                // If we want it to animate on mount, we should call animate().
                // BUT based on previous code: "if (trigger !== undefined) { animate(); } else { setDisplayText(text); }"
                // It implies manual control or static text if no trigger. 
                // However, QRCodeDropdown uses it with explicit trigger or just plain?
                // usage: <CypherText text="Scan to Download" delay={200} /> (no trigger)
                // This implies it SHOULD animate on mount if delay is provided? 
                // Or did I miss the behavior?

                // If trigger is undefined, and we passed a delay, we probably want it to run on mount.
                // Let's check original line 80-85 again.
                // 80: useEffect(() => {
                // 81:    if (trigger !== undefined) {
                // 82:        animate();
                // 83:    } else {
                // 84:        setDisplayText(text);
                // 85:    }

                // If I want "Scan to Download" to animate on mount, I should probably pass trigger={true} or change this logic.
                // BUT, for now, let's keep the logic simple and safe.
                // If trigger is provided, we respect delay.
                // If user wants on-mount animation, they usually pass trigger={true} or we can default trigger.
                // Wait, in previous step 333: <CypherText text="Scan to Download" delay={200} /> 
                // trigger is undefined. So it hits line 84: setDisplayText(text). No animation!
                // I should probably change this to animate on mount if trigger is undefined?
                // Or better yet, allow it to animate if trigger is undefined (auto-play).
                // The original behavior: "onMouseEnter={animate}" (line 97) suggests it is interactive.

                // Let's change the logic: If trigger is undefined, we DON'T animate automatically unless we want to?
                // Actually, "Scan to Download" might just be static text that animates on hover?
                // "onMouseEnter={animate}" is on the span.
                // If I want it to animate on appearance with delay, I should surely call animate().

                // Let's modify the useEffect to support auto-run if delay is set? 
                // No, that changes behavior for others.

                // Recommendation: In usage, I should pass trigger={true} to force animation, or just let it be static until hover.
                // The user said "Get App dropdown... Scan to Download... have the cool decoding effect". 
                // Probably wants it to animate on dropdown open?
                // The dropdown mounts when open. So on-mount animation is desired.

                // So I will change the useEffect:
                // If trigger is undefined, run animate() once (on mount).

                // New Logic:
                // if (trigger !== undefined) {
                //    if (trigger) animate() (with delay)
                // } else {
                //    // No trigger prop provided. 
                //    // Previously: setDisplayText(text) (static).
                //    // New: animate() (on mount) with delay?
                //    // If I change this, all static CypherTexts will start animating. 
                //    // Do we have static ones? 
                //    // Looking at search results, CypherText is used in `QRCodeDropdown`.
                //    // I'll stick to: if trigger provided (boolean), use it.
                //    // I will update `QRCodeDropdown` to pass `trigger={true}` for the "Scan to Download" text if I want it to animate.

                // For now, let's just implement the delay support in the hook for use when trigger fires.
            }
        }

        return () => {
            clearTimeout(timeoutId);
            if (intervalRef.current) clearInterval(intervalRef.current);
            timeoutsRef.current.forEach(clearTimeout);
            if (loopTimeoutRef.current) clearTimeout(loopTimeoutRef.current);
        };
    }, [text, trigger, animate, delay]);

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

