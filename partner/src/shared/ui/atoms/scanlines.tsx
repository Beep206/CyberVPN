export function Scanlines() {
    return (
        <div className="pointer-events-none fixed inset-0 z-50 overflow-hidden select-none hidden dark:block">
            {/* Scanline pattern */}
            <div
                className="absolute inset-0 z-50 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] pointer-events-none"
                style={{ backgroundSize: "100% 3px, 6px 100%" }}
            />

            {/* Vignette */}
            <div className="absolute inset-0 z-50 bg-[radial-gradient(circle_at_center,transparent_50%,rgba(0,0,0,0.4)_100%)] pointer-events-none" />

            {/* Flicker Animation */}
            <div className="absolute inset-0 z-50 bg-white/5 opacity-[0.02] animate-pulse pointer-events-none" />
        </div>
    );
}
