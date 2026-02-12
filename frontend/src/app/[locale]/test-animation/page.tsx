"use client";

import React from "react";
import { InceptionButton } from "@/components/ui/InceptionButton";

export default function AnimationTestPage() {
    return (
        <div className="min-h-screen w-full bg-[#0a0a0a] flex flex-col items-center justify-center space-y-20 p-10 overflow-hidden">

            <div className="text-center space-y-4">
                <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                    Inception Effect Test
                </h1>
                <p className="text-gray-400">Click the elements below to see the effect.</p>
            </div>

            {/* Standard Button */}
            <div className="flex gap-10">
                <InceptionButton className="cursor-pointer">
                    <button className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl shadow-lg shadow-blue-500/20 active:scale-95 transition-transform">
                        Destruct Me
                    </button>
                </InceptionButton>

                <InceptionButton className="cursor-pointer">
                    <div className="px-8 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-bold rounded-xl shadow-lg shadow-purple-500/20 hover:scale-105 transition-transform flex items-center gap-2">
                        <span>✨</span>
                        <span>Magic Button</span>
                    </div>
                </InceptionButton>
            </div>

            {/* Card Element */}
            <InceptionButton className="cursor-pointer">
                <div className="w-80 h-48 bg-gray-900 border border-gray-800 rounded-2xl p-6 flex flex-col justify-between hover:border-gray-700 transition-colors group">
                    <div className="flex items-start justify-between">
                        <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                            <span className="text-2xl">⚡</span>
                        </div>
                        <span className="text-xs font-mono text-gray-500">SYS.01</span>
                    </div>

                    <div>
                        <h3 className="text-xl font-bold text-white mb-1">Energy Core</h3>
                        <p className="text-sm text-gray-400">Stable operation at 98% efficiency.</p>
                    </div>
                </div>
            </InceptionButton>

            {/* Large Block */}
            <InceptionButton className="cursor-pointer">
                <div className="relative w-[500px] h-[200px] rounded-3xl overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                        src="https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?q=80&w=1000&auto=format&fit=crop"
                        alt="Abstract"
                        className="absolute inset-0 w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                        <h2 className="text-4xl font-black text-white tracking-tighter uppercase italic">
                            Unstoppable
                        </h2>
                    </div>
                </div>
            </InceptionButton>

        </div>
    );
}
