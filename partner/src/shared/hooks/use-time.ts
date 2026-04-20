'use client';

import { useState, useEffect } from 'react';

export function useTime() {
    const [time, setTime] = useState<string>('');

    useEffect(() => {
        const updateTime = () => setTime(new Date().toISOString().split('T')[1].split('.')[0] + ' UTC');
        updateTime();
        const timer = setInterval(updateTime, 1000);
        return () => clearInterval(timer);
    }, []);

    return time;
}
