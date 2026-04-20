import type { ReactNode } from 'react';
import { DocsInteractiveRail } from './docs-interactive-rail';

export function DocsContainer({ content }: { content?: ReactNode }) {
    return (
        <div
            data-testid="docs-container-layout"
            className="grid grid-cols-1 gap-8 px-4 pt-12 pb-24 lg:grid-cols-12 lg:gap-10 lg:px-6 lg:pb-32"
        >
            <div
                data-testid="docs-container-content"
                className="order-1 lg:order-2 lg:col-span-6 relative z-10 w-full overflow-x-hidden"
            >
                <div className="w-full flex-1 max-w-3xl space-y-24 pb-24 lg:space-y-32 lg:pb-[55vh]">
                    {content}
                </div>
            </div>

            <DocsInteractiveRail />
        </div>
    );
}
