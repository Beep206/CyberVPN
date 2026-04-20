'use client';

import dynamic from 'next/dynamic';

const FinanceOperationsPageNoSsr = dynamic(
  () => import('./finance-operations-page').then((mod) => mod.FinanceOperationsPage),
  { ssr: false },
);

export function FinanceOperationsPageEntry() {
  return <FinanceOperationsPageNoSsr />;
}
