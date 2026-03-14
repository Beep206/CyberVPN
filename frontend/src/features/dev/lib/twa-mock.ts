export function injectTwaMock() {
    if (typeof window === 'undefined') return;

    try {
        const saved = localStorage.getItem('DEV_TWA_MOCK');
        if (!saved) return;
        
        const config = JSON.parse(saved);
        if (!config.enabled) return;

        // Skip if we are actually inside Telegram
        if ((window as any).Telegram?.WebApp?.initData) return;

        console.log('[Dev Tools] Injecting TWA Mock Context...');

        const mockInitDataUnsafe = {
            query_id: "mock_query_id",
            user: config.user,
            auth_date: Math.floor(Date.now() / 1000),
            hash: "mock_hash"
        };
        
        const mockInitData = new URLSearchParams({
            query_id: mockInitDataUnsafe.query_id,
            user: JSON.stringify(mockInitDataUnsafe.user),
            auth_date: mockInitDataUnsafe.auth_date.toString(),
            hash: mockInitDataUnsafe.hash
        }).toString();

        (window as any).Telegram = {
            WebApp: {
                initData: mockInitData,
                initDataUnsafe: mockInitDataUnsafe,
                version: '7.0',
                platform: config.platform,
                colorScheme: config.theme,
                themeParams: {
                    bg_color: config.theme === 'dark' ? '#000000' : '#ffffff',
                    text_color: config.theme === 'dark' ? '#ffffff' : '#000000',
                    hint_color: '#a8a8a8',
                    link_color: '#3390ec',
                    button_color: '#3390ec',
                    button_text_color: '#ffffff',
                    secondary_bg_color: config.theme === 'dark' ? '#1c1c1d' : '#f0f0f0',
                },
                isExpanded: true,
                viewportHeight: window.innerHeight,
                viewportStableHeight: window.innerHeight,
                headerColor: '#000000',
                backgroundColor: '#000000',
                BackButton: { isVisible: false, onClick: () => {}, show: () => {}, hide: () => {} },
                MainButton: { 
                    text: 'CONTINUE', color: '#3390ec', textColor: '#ffffff', 
                    isVisible: false, isActive: true, isProgressVisible: false, 
                    setParams: () => {}, onClick: () => {}, show: () => {}, hide: () => {}, 
                    enable: () => {}, disable: () => {}, showProgress: () => {}, hideProgress: () => {} 
                },
                HapticFeedback: { impactOccurred: () => {}, notificationOccurred: () => {}, selectionChanged: () => {} },
                ready: () => {},
                expand: () => {},
                close: () => {},
            }
        };
    } catch {
        // ignore errors
    }
}
