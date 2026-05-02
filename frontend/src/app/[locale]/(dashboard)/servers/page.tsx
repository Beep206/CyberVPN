import { ErrorBoundary } from '@/shared/ui/error-boundary';
import { ServerAccessDashboard } from '@/widgets/server-access/server-access-dashboard';

export default function ServersPage() {
    return (
        <div className="mx-auto w-full max-w-7xl">
            <ErrorBoundary label="Server Access Dashboard">
                <ServerAccessDashboard />
            </ErrorBoundary>
        </div>
    );
}
