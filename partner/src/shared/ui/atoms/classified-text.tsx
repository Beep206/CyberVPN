'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export function ClassifiedText({ text }: { text: string }) {
    const [isRevealed, setIsRevealed] = useState(false);

    // Split text into tokens for a blocky redaction look
    const tokens = text.split(/(\s+)/);

    return (
        <span 
            className="relative cursor-crosshair group inline-block"
            onMouseEnter={() => setIsRevealed(true)}
            onMouseLeave={() => setIsRevealed(false)}
        >
            {/* The scanning laser line */}
            <AnimatePresence>
                {isRevealed && (
                    <motion.span
                        initial={{ left: 0, opacity: 0 }}
                        animate={{ left: '100%', opacity: 1 }}
                        exit={{ left: '100%', opacity: 0 }}
                        transition={{ duration: 1.5, ease: "linear", repeat: Infinity }}
                        className="absolute top-0 bottom-0 w-1 bg-neon-cyan z-20 shadow-[0_0_10px_#00ffff]"
                    />
                )}
            </AnimatePresence>

            {tokens.map((token, idx) => {
                if (!token.trim()) return <span key={idx}>{token}</span>; // Preserve whitespace

                return (
                    <span key={idx} className="relative inline-block mx-[1px]">
                        {/* The actual text (hidden initially) */}
                        <span className={`relative z-10 font-mono transition-colors duration-300 ${isRevealed ? 'text-neon-cyan' : 'text-transparent'}`}>
                            {token}
                        </span>

                        {/* Redaction block */}
                        <motion.span
                            initial={false}
                            animate={{
                                opacity: isRevealed ? 0 : 1,
                                scaleY: isRevealed ? 0 : 1
                            }}
                            transition={{ duration: 0.2, delay: idx * 0.01 }}
                            className="absolute inset-0 bg-white z-20 origin-bottom"
                        />
                        
                        {/* Redaction block (digital noise overlay) */}
                        {!isRevealed && (
                            <span
                                className="absolute inset-0 mix-blend-overlay opacity-50 z-30 pointer-events-none"
                                style={{ backgroundImage: "url('/scanlines.png')" }}
                            />
                        )}
                    </span>
                );
            })}
        </span>
    );
}
