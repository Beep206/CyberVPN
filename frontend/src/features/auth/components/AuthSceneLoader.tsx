'use client';

import dynamic from 'next/dynamic';
import { memo } from 'react';

// Dynamic import with SSR disabled to prevent WebGL context issues
const AuthScene3DWrapper = dynamic(
    () => import('@/3d/scenes/AuthScene3D').then((mod) => mod.AuthScene3D),
    {
        ssr: false,
        loading: () => <div className="absolute inset-0 z-0 bg-terminal-bg" />,
    }
);

export const AuthSceneLoader = memo(function AuthSceneLoader() {
    return <AuthScene3DWrapper />;
});
