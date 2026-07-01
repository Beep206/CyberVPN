type DevToolsProps = {
  closeButtonLabel: string;
  openButtonLabel: string;
};

export async function DevTools({ closeButtonLabel, openButtonLabel }: DevToolsProps) {
  if (
    process.env.NODE_ENV !== 'development' ||
    process.env.NEXT_PUBLIC_DEV_TOOLS_ENABLED !== 'true'
  ) {
    return null;
  }

  const { DevToolsClient } = await import('./dev-tools-client');

  return (
    <DevToolsClient
      closeButtonLabel={closeButtonLabel}
      openButtonLabel={openButtonLabel}
    />
  );
}
