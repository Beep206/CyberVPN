class RenderProfiler {
    private observer: MutationObserver | null = null;
    public isFlashing = false;

    start() {
        if (typeof window === 'undefined') return;
        
        let shouldFlash = false;
        try {
            shouldFlash = localStorage.getItem('DEV_PAINT_FLASHING') === 'true';
        } catch { /* ignore */ }
        
        this.isFlashing = shouldFlash;
        if (this.isFlashing) this.enableObserver();
    }

    toggle(active: boolean) {
        this.isFlashing = active;
        if (typeof window !== 'undefined') {
            localStorage.setItem('DEV_PAINT_FLASHING', active ? 'true' : 'false');
        }
        if (active) {
            this.enableObserver();
        } else {
            this.disableObserver();
        }
    }

    private enableObserver() {
        if (typeof window === 'undefined' || this.observer) return;
        
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                const target = mutation.target as HTMLElement;
                // Ignore text nodes, the dev panel itself, or already flashing elements
                if (target.nodeType === 1 
                    && !target.closest('#dev-panel-root') 
                    && !target.classList?.contains('dev-paint-flash')
                    && !(target as any)._isFlashing) {
                    
                    const rect = target.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0 || rect.width > window.innerWidth || rect.height > window.innerHeight) return;

                    (target as any)._isFlashing = true;

                    const flash = document.createElement('div');
                    flash.className = 'dev-paint-flash pointer-events-none fixed z-[99999] transition-opacity duration-500 ease-out';
                    
                    const colors = ['rgba(255,100,200,0.5)', 'rgba(100,255,200,0.5)', 'rgba(100,200,255,0.5)', 'rgba(255,255,100,0.5)'];
                    const randColor = colors[Math.floor(Math.random() * colors.length)];
                    
                    flash.style.backgroundColor = randColor;
                    flash.style.border = `1px solid ${randColor.replace('0.5', '1')}`;
                    flash.style.left = `${rect.left}px`;
                    flash.style.top = `${rect.top}px`;
                    flash.style.width = `${rect.width}px`;
                    flash.style.height = `${rect.height}px`;

                    document.body.appendChild(flash);

                    requestAnimationFrame(() => {
                        flash.style.opacity = '1';
                        setTimeout(() => {
                            flash.style.opacity = '0';
                            setTimeout(() => {
                                flash.remove();
                                (target as any)._isFlashing = false;
                            }, 500);
                        }, 50);
                    });
                }
            });
        });

        observer.observe(document.body, {
            attributes: true,
            childList: true,
            characterData: true,
            subtree: true,
            attributeFilter: ['class', 'style', 'src', 'href', 'value']
        });

        this.observer = observer;
    }

    private disableObserver() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        if (typeof document !== 'undefined') {
            document.querySelectorAll('.dev-paint-flash').forEach(el => el.remove());
        }
    }
}

export const renderProfiler = new RenderProfiler();
