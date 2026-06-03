'use client';

import { useEffect, useState, type ComponentType } from 'react';

const AUTH_SCENE_FALLBACK = <div className="absolute inset-0 z-0 bg-terminal-bg" />;

function canCreateWebGLContext(): boolean {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('webgl2') || canvas.getContext('webgl');

    return Boolean(context);
}

export function AuthSceneLoader() {
    const [AuthScene, setAuthScene] = useState<ComponentType | null>(null);

    useEffect(() => {
        let cancelled = false;

        if (!canCreateWebGLContext()) {
            return () => {
                cancelled = true;
            };
        }

        void import('@/3d/scenes/AuthScene3D').then((mod) => {
            if (!cancelled) {
                setAuthScene(() => mod.AuthScene3D);
            }
        });

        return () => {
            cancelled = true;
        };
    }, []);

    return AuthScene ? <AuthScene /> : AUTH_SCENE_FALLBACK;
}
