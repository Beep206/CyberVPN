import { cn } from "@/lib/utils";
import type { ServerStatus } from "@/entities/server/model/types";

interface ServerStatusDotProps {
    status: ServerStatus;
    className?: string;
}

const statusColorMap: Record<ServerStatus, string> = {
    online: "bg-server-online shadow-server-online",
    offline: "bg-server-offline shadow-[0_0_10px_var(--color-server-offline)]",
    warning: "bg-server-warning shadow-[0_0_10px_var(--color-server-warning)]",
    maintenance: "bg-server-maintenance shadow-[0_0_10px_var(--color-server-maintenance)]",
};

export function ServerStatusDot({ status, className }: ServerStatusDotProps) {
    return (
        <span className={cn("relative flex h-3 w-3", className)}>
            <span
                className={cn(
                    "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
                    statusColorMap[status]
                )}
            />
            <span
                className={cn(
                    "relative inline-flex rounded-full h-3 w-3",
                    statusColorMap[status]
                )}
            />
        </span>
    );
}
