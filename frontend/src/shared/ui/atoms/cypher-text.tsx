'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { useMotionCapability } from '@/shared/hooks/use-motion-capability';

interface CypherTextProps {
    text: string;
    className?: string;
    characters?: string;
    speed?: number;
    revealSpeed?: number;
    trigger?: unknown;
    loop?: boolean;
    loopDelay?: number;
    delay?: number;
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
    delay = 0,
}: CypherTextProps) {
    const { allowAmbientAnimations, allowPointerEffects } = useMotionCapability();
    const [displayText, setDisplayText] = useState(text);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const timeoutRefs = useRef<ReturnType<typeof setTimeout>[]>([]);
    const animateRef = useRef<() => void>(() => {});
    const textChars = useMemo(() => text.split(''), [text]);

    const clearTimers = useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }

        timeoutRefs.current.forEach(clearTimeout);
        timeoutRefs.current = [];
    }, []);

    const queueDisplayReset = useCallback(() => {
        const timeout = setTimeout(() => {
            setDisplayText(text);
        }, 0);

        timeoutRefs.current.push(timeout);
    }, [text]);

    const animate = useCallback(() => {
        if (!allowAmbientAnimations) {
            queueDisplayReset();
            return;
        }

        clearTimers();
        let revealIndex = 0;

        intervalRef.current = setInterval(() => {
            const nextText = textChars.map((char, index) => {
                if (index < revealIndex || char === ' ') {
                    return char;
                }

                return characters[Math.floor(Math.random() * characters.length)];
            }).join('');

            setDisplayText(nextText);
        }, speed);

        for (let i = 0; i <= textChars.length; i += 1) {
            const timeout = setTimeout(() => {
                revealIndex = i;

                if (i === textChars.length) {
                    clearTimers();
                    setDisplayText(text);

                    if (loop) {
                        const loopTimeout = setTimeout(() => {
                            animateRef.current();
                        }, loopDelay);

                        timeoutRefs.current.push(loopTimeout);
                    }
                }
            }, i * revealSpeed);

            timeoutRefs.current.push(timeout);
        }
    }, [allowAmbientAnimations, characters, clearTimers, loop, loopDelay, queueDisplayReset, revealSpeed, speed, text, textChars]);

    useEffect(() => {
        animateRef.current = animate;
    }, [animate]);

    useEffect(() => {
        clearTimers();
        queueDisplayReset();
    }, [clearTimers, queueDisplayReset, text]);

    useEffect(() => {
        if (!allowAmbientAnimations) {
            clearTimers();
            queueDisplayReset();
            return;
        }

        const shouldAutoPlay = loop || delay > 0 || trigger === true;

        if (!shouldAutoPlay && trigger === undefined) {
            queueDisplayReset();
            return;
        }

        const timeout = setTimeout(() => {
            animate();
        }, delay);

        timeoutRefs.current.push(timeout);

        return () => {
            clearTimeout(timeout);
        };
    }, [allowAmbientAnimations, animate, clearTimers, delay, loop, queueDisplayReset, text, trigger]);

    useEffect(() => clearTimers, [clearTimers]);

    return (
        <span
            aria-label={text}
            className={cn('font-mono inline-block will-change-transform', className)}
            onMouseEnter={allowPointerEffects ? animate : undefined}
        >
            <span aria-hidden="true">{displayText}</span>
        </span>
    );
}
