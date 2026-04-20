import { cn } from "../lib/utils";

type PageSkeletonProps = {
  fullscreen?: boolean;
};

function SkeletonLine({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "h-3 rounded-full border border-white/20 bg-[linear-gradient(90deg,color-mix(in_oklab,var(--panel-subtle)_88%,white),color-mix(in_oklab,var(--panel-surface)_94%,white),color-mix(in_oklab,var(--panel-subtle)_88%,white))] animate-pulse",
        className
      )}
    />
  );
}

export function PageSkeleton({ fullscreen = false }: PageSkeletonProps) {
  return (
    <div
      className={cn(
        "flex min-h-full flex-col gap-6",
        fullscreen && "min-h-screen bg-background px-6 py-10"
      )}
    >
      <div className="space-y-3">
        <SkeletonLine className="h-4 w-32" />
        <SkeletonLine className="h-8 w-72 max-w-full bg-border/35" />
        <SkeletonLine className="w-96 max-w-full" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="rounded-3xl border border-border/45 bg-[color:var(--panel-surface)]/78 p-5 shadow-[var(--panel-shadow)] backdrop-blur-xl">
          <div className="space-y-3">
            <SkeletonLine className="w-28" />
            <SkeletonLine className="h-10 w-full bg-border/35" />
            <SkeletonLine className="h-10 w-5/6" />
            <SkeletonLine className="h-10 w-4/6" />
          </div>
        </div>

        <div className="rounded-3xl border border-border/40 bg-[color:var(--panel-subtle)]/72 p-5 shadow-[var(--panel-shadow)] backdrop-blur-xl">
          <div className="space-y-3">
            <SkeletonLine className="w-24" />
            <SkeletonLine className="h-24 w-full bg-border/35" />
            <SkeletonLine className="w-3/4" />
            <SkeletonLine className="w-2/3" />
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-3xl border border-border/35 bg-[color:var(--panel-surface)]/65 p-4 shadow-[var(--panel-shadow)] backdrop-blur-lg">
          <SkeletonLine className="w-16" />
          <SkeletonLine className="mt-4 h-8 w-24 bg-border/35" />
        </div>
        <div className="rounded-3xl border border-border/35 bg-[color:var(--panel-surface)]/65 p-4 shadow-[var(--panel-shadow)] backdrop-blur-lg">
          <SkeletonLine className="w-20" />
          <SkeletonLine className="mt-4 h-8 w-28 bg-border/35" />
        </div>
        <div className="rounded-3xl border border-border/35 bg-[color:var(--panel-surface)]/65 p-4 shadow-[var(--panel-shadow)] backdrop-blur-lg">
          <SkeletonLine className="w-24" />
          <SkeletonLine className="mt-4 h-8 w-20 bg-border/35" />
        </div>
      </div>
    </div>
  );
}
