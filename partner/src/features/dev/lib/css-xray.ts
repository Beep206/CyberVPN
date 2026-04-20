class CssXRay {
    public isActive = false;

    start() {
        if (typeof window === 'undefined') return;
        try {
            this.isActive = localStorage.getItem('DEV_CSS_XRAY') === 'true';
        } catch { /* ignore */ }
        
        if (this.isActive) {
            this.applyStyles();
        }
    }

    toggle(active: boolean) {
        this.isActive = active;
        if (typeof window !== 'undefined') {
            localStorage.setItem('DEV_CSS_XRAY', active ? 'true' : 'false');
        }
        if (active) {
            this.applyStyles();
        } else {
            this.removeStyles();
        }
    }

    private applyStyles() {
        if (typeof document === 'undefined') return;
        const id = 'dev-css-xray-styles';
        if (!document.getElementById(id)) {
            const styleEl = document.createElement('style');
            styleEl.id = id;
            styleEl.textContent = `
                * {
                    outline: 1px solid rgba(0, 255, 255, 0.5) !important;
                    background: rgba(0, 0, 0, 0.1) !important;
                }
                #dev-panel-root, #dev-panel-root * {
                    outline: none !important;
                    background: inherit !important;
                }
            `;
            document.head.appendChild(styleEl);
        }
    }

    private removeStyles() {
        if (typeof document === 'undefined') return;
        const id = 'dev-css-xray-styles';
        const el = document.getElementById(id);
        if (el) el.remove();
    }
}

export const cssXRay = new CssXRay();
