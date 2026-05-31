import { CatalogPreviewConsole } from '@/features/commerce/components/catalog-preview-console';
import { getCommercePageMetadata } from '@/features/commerce/lib/page-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  return getCommercePageMetadata(locale, 'catalogPreview');
}

export default function CommerceCatalogPreviewPage() {
  return <CatalogPreviewConsole />;
}
