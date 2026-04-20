export async function DevTools() {
  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  const { DevToolsClient } = await import('./dev-tools-client');

  return <DevToolsClient />;
}
