'use client';

import { useState, useEffect } from 'react';
import { useInView } from 'motion/react';
import { useRef } from 'react';

interface ScrambleTextProps {
    text: string;
    className?: string;
    revealDelay?: number;
    scrambleSpeed?: number;
    triggerOnHover?: boolean;
}

export function ScrambleText({
    text,
    className,
    revealDelay = 0,
    scrambleSpeed = 30,
    triggerOnHover = false
}: ScrambleTextProps) {
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&";
    const [display, setDisplay] = useState(text);
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.5 });
    const [isHovered, setIsHovered] = useState(false);

    // Internal state to track if interaction is happening
    const isAnimating = useRef(false);

    const scramble = () => {
        if (isAnimating.current) return;
        isAnimating.current = true;

        let iterations = 0;
        const interval = setInterval(() => {
            setDisplay(
                text
                    .split("")
                    .map((letter, index) => {
                        if (index < iterations) {
                            return text[index];
                        }
                        return letters[Math.floor(Math.random() * letters.length)];
                    })
                    .join("")
            );

            if (iterations >= text.length) {
                clearInterval(interval);
                isAnimating.current = false;
            }
            iterations += 1 / 3;
        }, scrambleSpeed);

        return () => clearInterval(interval);
    };

    useEffect(() => {
        if (isInView) {
            const timeout = setTimeout(() => {
                scramble();
            }, revealDelay);
            return () => clearTimeout(timeout);
        }
    }, [isInView, text, revealDelay]);

    const handleMouseEnter = () => {
        if (triggerOnHover) {
            scramble();
        }
        setIsHovered(true);
    };

    const handleMouseLeave = () => {
        setIsHovered(false);
    };

    return (
        <span
            ref={ref}
            className={className}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            {display}
        </span>
    );
}
