'use client';

import dynamic from 'next/dynamic';

const SettingsFoundationPageNoSsr = dynamic(
  () => import('./settings-foundation-page').then((mod) => mod.SettingsFoundationPage),
  { ssr: false },
);

export function SettingsFoundationPageEntry() {
  return <SettingsFoundationPageNoSsr />;
}
