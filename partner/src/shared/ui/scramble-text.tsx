'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useInView } from 'motion/react';
import { useMotionCapability } from '@/shared/hooks/use-motion-capability';

interface ScrambleTextProps {
    text: string;
    className?: string;
    revealDelay?: number;
    scrambleSpeed?: number;
    triggerOnHover?: boolean;
    loop?: boolean;
    loopDelay?: number;
}

const SCRAMBLE_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&';

export function ScrambleText({
    text,
    className,
    revealDelay = 0,
    scrambleSpeed = 30,
    triggerOnHover = false,
    loop = false,
    loopDelay = 2000,
}: ScrambleTextProps) {
    const { allowAmbientAnimations, allowPointerEffects } = useMotionCapability();
    const [display, setDisplay] = useState(text);
    const ref = useRef<HTMLSpanElement>(null);
    const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const isAnimatingRef = useRef(false);
    const isInView = useInView(ref, { once: !loop, amount: 0.5 });
    const textChars = useMemo(() => text.split(''), [text]);

    const queueDisplayReset = useCallback(() => {
        const timeout = setTimeout(() => {
            setDisplay(text);
        }, 0);

        timersRef.current.push(timeout);
    }, [text]);

    const clearTimers = useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }

        timersRef.current.forEach(clearTimeout);
        timersRef.current = [];
        isAnimatingRef.current = false;
    }, []);

    const scramble = useCallback(() => {
        if (!allowAmbientAnimations || isAnimatingRef.current) {
            return;
        }

        clearTimers();
        isAnimatingRef.current = true;

        let iterations = 0;

        intervalRef.current = setInterval(() => {
            setDisplay(
                textChars
                    .map((letter, index) => {
                        if (index < iterations) {
                            return letter;
                        }

                        return SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)];
                    })
                    .join(''),
            );

            if (iterations >= textChars.length) {
                clearTimers();
                setDisplay(text);
            }

            iterations += 1 / 3;
        }, scrambleSpeed);
    }, [allowAmbientAnimations, clearTimers, scrambleSpeed, text, textChars]);

    useEffect(() => {
        clearTimers();
        queueDisplayReset();
    }, [clearTimers, queueDisplayReset, text]);

    useEffect(() => {
        if (!allowAmbientAnimations || !isInView) {
            clearTimers();
            queueDisplayReset();
            return;
        }

        const timeout = setTimeout(() => {
            scramble();
        }, revealDelay);

        timersRef.current.push(timeout);

        return () => {
            clearTimeout(timeout);
        };
    }, [allowAmbientAnimations, clearTimers, isInView, queueDisplayReset, revealDelay, scramble, text]);

    useEffect(() => {
        if (!allowAmbientAnimations || !loop || !isInView) {
            return;
        }

        const loopInterval = setInterval(() => {
            scramble();
        }, loopDelay + (textChars.length * scrambleSpeed) / 3);

        return () => {
            clearInterval(loopInterval);
        };
    }, [allowAmbientAnimations, isInView, loop, loopDelay, scramble, scrambleSpeed, textChars.length]);

    useEffect(() => clearTimers, [clearTimers]);

    const handleMouseEnter = () => {
        if (allowPointerEffects && triggerOnHover) {
            scramble();
        }
    };

    return (
        <span ref={ref} className={className} onMouseEnter={handleMouseEnter}>
            {display}
        </span>
    );
}
