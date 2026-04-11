'use client';

import { motion } from 'motion/react';

function SkeletonPulse({ className }: { className?: string }) {
  return (
    <motion.div
      className={`bg-grid-line/30 rounded ${className}`}
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
    />
  );
}

export function AuthFormSkeleton() {
  return (
    <div className="w-full max-w-md mx-auto p-8 space-y-6">
      {/* Title skeleton */}
      <div className="text-center space-y-2">
        <SkeletonPulse className="h-8 w-40 mx-auto" />
        <SkeletonPulse className="h-4 w-56 mx-auto" />
      </div>

      {/* Social buttons skeleton */}
      <div className="grid grid-cols-2 gap-3">
        <SkeletonPulse className="h-11 w-full" />
        <SkeletonPulse className="h-11 w-full" />
      </div>

      {/* Divider skeleton */}
      <div className="flex items-center gap-3">
        <SkeletonPulse className="h-px flex-1" />
        <SkeletonPulse className="h-4 w-8" />
        <SkeletonPulse className="h-px flex-1" />
      </div>

      {/* Form fields skeleton */}
      <div className="space-y-5">
        {/* Email field */}
        <div className="space-y-2">
          <SkeletonPulse className="h-4 w-16" />
          <SkeletonPulse className="h-12 w-full" />
        </div>

        {/* Password field */}
        <div className="space-y-2">
          <SkeletonPulse className="h-4 w-20" />
          <SkeletonPulse className="h-12 w-full" />
        </div>

        {/* Remember me / forgot password */}
        <div className="flex items-center justify-between">
          <SkeletonPulse className="h-4 w-24" />
          <SkeletonPulse className="h-4 w-28" />
        </div>

        {/* Submit button */}
        <SkeletonPulse className="h-12 w-full" />
      </div>

      {/* Footer link skeleton */}
      <div className="flex justify-center gap-2">
        <SkeletonPulse className="h-4 w-32" />
        <SkeletonPulse className="h-4 w-16" />
      </div>
    </div>
  );
}

export function AuthLoadingOverlay({ message }: { message?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-terminal-bg/80 backdrop-blur-sm"
    >
      <div className="flex flex-col items-center gap-4">
        {/* Animated spinner */}
        <motion.div
          className="w-12 h-12 border-4 border-neon-cyan/20 border-t-neon-cyan rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        />
        {message && (
          <p className="text-sm font-mono text-muted-foreground animate-pulse">
            {message}
          </p>
        )}
      </div>
    </motion.div>
  );
}
