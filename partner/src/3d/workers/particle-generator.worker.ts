const MAX_PARTICLE_COUNT = 10_000;

self.onmessage = (e: MessageEvent<{ count: number }>) => {
    if (e.origin && e.origin !== self.location.origin) {
        return;
    }

    const requestedCount = Math.trunc(Number(e.data?.count));
    if (!Number.isFinite(requestedCount) || requestedCount <= 0) {
        return;
    }

    const count = Math.min(requestedCount, MAX_PARTICLE_COUNT);
    const positions = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);
    const phases = new Float32Array(count);

    for (let i = 0; i < count; i++) {
        const r = 4 + Math.random() * 8;
        const theta = Math.random() * 2 * Math.PI;
        const phi = Math.acos(2 * Math.random() - 1);

        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = r * Math.cos(phi);

        velocities[i * 3] = (Math.random() - 0.5) * 0.02;
        velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.02;
        velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.02;

        phases[i] = Math.random() * Math.PI * 2;
    }

    self.postMessage(
        { positions, velocities, phases },
        { transfer: [positions.buffer, velocities.buffer, phases.buffer] }
    );
};
