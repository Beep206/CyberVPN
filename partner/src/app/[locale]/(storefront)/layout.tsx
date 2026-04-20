import { QueryProvider } from '@/app/providers/query-provider';

export default function StorefrontLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <QueryProvider>{children}</QueryProvider>;
}
