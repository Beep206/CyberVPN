'use client';

export interface MobileViewportSpec {
  id: string;
  width: number;
  height: number;
  finePointer: boolean;
  reducedMotion: boolean;
  shell: 'browser' | 'telegram-webview';
}

export const MOBILE_VIEWPORTS = {
  iphoneSafari: {
    id: 'iphone-safari',
    width: 390,
    height: 844,
    finePointer: false,
    reducedMotion: false,
    shell: 'browser',
  },
  largeIphone: {
    id: 'large-iphone',
    width: 430,
    height: 932,
    finePointer: false,
    reducedMotion: false,
    shell: 'browser',
  },
  androidChrome: {
    id: 'android-chrome',
    width: 412,
    height: 915,
    finePointer: false,
    reducedMotion: false,
    shell: 'browser',
  },
  smallAndroid: {
    id: 'small-android',
    width: 360,
    height: 740,
    finePointer: false,
    reducedMotion: false,
    shell: 'browser',
  },
  tabletPortrait: {
    id: 'tablet-portrait',
    width: 834,
    height: 1112,
    finePointer: false,
    reducedMotion: false,
    shell: 'browser',
  },
  tabletLandscape: {
    id: 'tablet-landscape',
    width: 1112,
    height: 834,
    finePointer: true,
    reducedMotion: false,
    shell: 'browser',
  },
  telegramWebView: {
    id: 'telegram-webview',
    width: 390,
    height: 844,
    finePointer: false,
    reducedMotion: false,
    shell: 'telegram-webview',
  },
} as const satisfies Record<string, MobileViewportSpec>;

export type MobileViewportId = keyof typeof MOBILE_VIEWPORTS;

export function createMatchMediaMock({
  finePointer,
  reducedMotion,
}: Pick<MobileViewportSpec, 'finePointer' | 'reducedMotion'>) {
  return (query: string) => {
    const matches =
      (query.includes('pointer: fine') || query.includes('hover: hover'))
        ? finePointer
        : query.includes('prefers-reduced-motion: reduce')
          ? reducedMotion
          : false;

    return {
      matches,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    };
  };
}

export function setMockViewport(
  viewport: MobileViewportSpec,
  target: Window = window,
) {
  Object.defineProperty(target, 'innerWidth', {
    configurable: true,
    writable: true,
    value: viewport.width,
  });

  Object.defineProperty(target, 'innerHeight', {
    configurable: true,
    writable: true,
    value: viewport.height,
  });

  target.matchMedia = createMatchMediaMock(viewport) as typeof window.matchMedia;
  target.dispatchEvent(new Event('resize'));
}
