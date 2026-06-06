import {
  configure,
  getQueriesForElement,
  prettyDOM,
  type BoundFunctions,
  type queries,
} from '@testing-library/dom';
export * from '@testing-library/dom';
import * as React from 'react';
import { createRoot, hydrateRoot, type Root } from 'react-dom/client';
import { act as reactDomAct } from 'react-dom/test-utils';

type ActEnvironmentGlobal = typeof globalThis & {
  IS_REACT_ACT_ENVIRONMENT?: boolean;
};

type TestWrapper = React.JSXElementConstructor<{
  children: React.ReactNode;
}>;

type RenderOptions = {
  baseElement?: HTMLElement;
  container?: HTMLElement;
  hydrate?: boolean;
  reactStrictMode?: boolean;
  wrapper?: TestWrapper;
  onRecoverableError?: (error: unknown, errorInfo: React.ErrorInfo) => void;
};

type RenderResult = BoundFunctions<typeof queries> & {
  asFragment: () => DocumentFragment;
  baseElement: HTMLElement;
  container: HTMLElement;
  debug: (
    element?: HTMLElement | HTMLElement[],
    maxLength?: number,
    options?: Parameters<typeof prettyDOM>[2]
  ) => void;
  rerender: (ui: React.ReactNode) => void;
  unmount: () => void;
};

const mountedContainers = new Set<HTMLElement>();
const mountedRootEntries: Array<{ container: HTMLElement; root: Root }> = [];

const actGlobal = globalThis as ActEnvironmentGlobal;
actGlobal.IS_REACT_ACT_ENVIRONMENT = true;

export const act = reactDomAct;

configure({
  unstable_advanceTimersWrapper: (callback) => act(callback),
  asyncWrapper: async (callback) => {
    const result = await callback();
    await new Promise((resolve) => {
      setTimeout(resolve, 0);
    });
    return result;
  },
  eventWrapper: (callback) => {
    let result: unknown;
    act(() => {
      result = callback();
    });
    return result;
  },
});

function wrapUi(ui: React.ReactNode, wrapper?: TestWrapper, reactStrictMode = false) {
  const wrapped = wrapper ? React.createElement(wrapper, null, ui) : ui;

  return reactStrictMode ? React.createElement(React.StrictMode, null, wrapped) : wrapped;
}

function removeMountedContainer(container: HTMLElement) {
  const mountedIndex = mountedRootEntries.findIndex((entry) => entry.container === container);

  if (mountedIndex >= 0) {
    mountedRootEntries.splice(mountedIndex, 1);
  }

  mountedContainers.delete(container);
}

function renderRoot(
  ui: React.ReactNode,
  {
    baseElement,
    container,
    reactStrictMode,
    root,
    wrapper,
  }: RenderOptions & {
    baseElement: HTMLElement;
    container: HTMLElement;
    root: Root;
  }
): RenderResult {
  act(() => {
    root.render(wrapUi(ui, wrapper, reactStrictMode));
  });

  return {
    ...getQueriesForElement(baseElement),
    asFragment: () => document.createRange().createContextualFragment(container.innerHTML),
    baseElement,
    container,
    debug: (element = baseElement, maxLength, options) => {
      const elements = Array.isArray(element) ? element : [element];
      for (const currentElement of elements) {
        console.error(prettyDOM(currentElement, maxLength, options));
      }
    },
    rerender: (rerenderUi) => {
      renderRoot(rerenderUi, {
        baseElement,
        container,
        reactStrictMode,
        root,
        wrapper,
      });
    },
    unmount: () => {
      act(() => {
        root.unmount();
      });
      removeMountedContainer(container);
    },
  };
}

export function render(ui: React.ReactNode, options: RenderOptions = {}): RenderResult {
  const {
    baseElement = document.body,
    container = baseElement.appendChild(document.createElement('div')),
    hydrate = false,
    onRecoverableError,
    reactStrictMode,
    wrapper,
  } = options;

  let root = mountedRootEntries.find((entry) => entry.container === container)?.root;

  if (!root) {
    const element = wrapUi(ui, wrapper, reactStrictMode);
    root = hydrate
      ? hydrateRoot(container, element, { onRecoverableError })
      : createRoot(container, { onRecoverableError });

    mountedRootEntries.push({ container, root });
    mountedContainers.add(container);
  }

  return renderRoot(ui, {
    baseElement,
    container,
    reactStrictMode,
    root,
    wrapper,
  });
}

export function cleanup() {
  for (const { container, root } of [...mountedRootEntries]) {
    act(() => {
      root.unmount();
    });

    if (container.parentNode === document.body) {
      document.body.removeChild(container);
    }

    mountedContainers.delete(container);
  }

  mountedRootEntries.length = 0;
}

type RenderHookOptions<Props> = RenderOptions & {
  initialProps?: Props;
};

export function renderHook<Result, Props = undefined>(
  renderCallback: (initialProps: Props) => Result,
  options: RenderHookOptions<Props> = {}
) {
  const { initialProps, ...renderOptions } = options;
  const result = { current: undefined as Result };

  function TestComponent({ renderCallbackProps }: { renderCallbackProps: Props }) {
    const pendingResult = renderCallback(renderCallbackProps);

    React.useEffect(() => {
      result.current = pendingResult;
    });

    return null;
  }

  const { rerender: baseRerender, unmount } = render(
    React.createElement(TestComponent, { renderCallbackProps: initialProps as Props }),
    renderOptions
  );

  return {
    result,
    rerender: (rerenderCallbackProps: Props) =>
      baseRerender(
        React.createElement(TestComponent, { renderCallbackProps: rerenderCallbackProps })
      ),
    unmount,
  };
}
