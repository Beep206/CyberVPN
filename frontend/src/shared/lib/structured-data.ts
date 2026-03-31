import type {
  BreadcrumbList,
  CollectionPage,
  FAQPage,
  ListItem,
  Offer,
  SoftwareApplication,
  TechArticle,
  WithContext,
} from 'schema-dts';
import { getHtmlLanguageAttributes, SITE_URL } from '@/shared/lib/site-metadata';
import { toAbsoluteLocalizedUrl } from '@/shared/lib/seo-route-policy';

export type StructuredFaqItem = {
  question: string;
  answer: string;
};

export type StructuredBreadcrumbItem = {
  name: string;
  path: string;
};

export type StructuredOfferItem = {
  name: string;
  description: string;
  price: string;
  priceCurrency?: string;
  url: string;
};

type StructuredDataBase = {
  locale?: string;
  path: string;
  title: string;
  description: string;
};

function resolveSchemaLocale(locale?: string) {
  return getHtmlLanguageAttributes(locale).lang;
}

function buildPublisherOrganization() {
  return {
    '@type': 'Organization' as const,
    name: 'CyberVPN',
    url: SITE_URL,
  };
}

export function buildBreadcrumbListStructuredData({
  locale,
  items,
}: {
  locale?: string;
  items: readonly StructuredBreadcrumbItem[];
}): WithContext<BreadcrumbList> {
  const resolvedLocale = resolveSchemaLocale(locale);

  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map<ListItem>((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: toAbsoluteLocalizedUrl(resolvedLocale, item.path),
    })),
  };
}

export function buildFaqPageStructuredData({
  locale,
  path,
  title,
  description,
  faqs,
}: StructuredDataBase & {
  faqs: readonly StructuredFaqItem[];
}): WithContext<FAQPage> {
  const resolvedLocale = resolveSchemaLocale(locale);
  const url = toAbsoluteLocalizedUrl(resolvedLocale, path);

  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    name: title,
    description,
    inLanguage: resolvedLocale,
    url,
    mainEntityOfPage: url,
    mainEntity: faqs.map((faq) => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  };
}

export function buildCollectionPageStructuredData({
  locale,
  path,
  title,
  description,
  items,
}: StructuredDataBase & {
  items: readonly StructuredBreadcrumbItem[];
}): WithContext<CollectionPage> {
  const resolvedLocale = resolveSchemaLocale(locale);
  const url = toAbsoluteLocalizedUrl(resolvedLocale, path);

  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: title,
    description,
    inLanguage: resolvedLocale,
    url,
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: items.map<ListItem>((item, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: item.name,
        item: toAbsoluteLocalizedUrl(resolvedLocale, item.path),
      })),
    },
    publisher: buildPublisherOrganization(),
  };
}

export function buildTechArticleStructuredData({
  locale,
  path,
  title,
  description,
  sections,
}: StructuredDataBase & {
  sections: readonly string[];
}): WithContext<TechArticle> {
  const resolvedLocale = resolveSchemaLocale(locale);
  const url = toAbsoluteLocalizedUrl(resolvedLocale, path);

  return {
    '@context': 'https://schema.org',
    '@type': 'TechArticle',
    headline: title,
    name: title,
    description,
    inLanguage: resolvedLocale,
    url,
    mainEntityOfPage: url,
    articleSection: sections,
    proficiencyLevel: 'Beginner to Advanced',
    dependencies: 'CyberVPN core access, supported client device, and active network connectivity.',
    about: ['VPN', 'VLESS', 'Reality', 'Xray', 'Sing-box', 'API integration'],
    publisher: buildPublisherOrganization(),
  };
}

export function buildOfferStructuredData({
  locale,
  name,
  description,
  price,
  priceCurrency = 'USD',
  url,
}: {
  locale?: string;
  name: string;
  description: string;
  price: string;
  priceCurrency?: string;
  url: string;
}): Offer {
  const resolvedLocale = resolveSchemaLocale(locale);

  return {
    '@type': 'Offer',
    availability: 'https://schema.org/InStock',
    description,
    name,
    price,
    priceCurrency,
    url: toAbsoluteLocalizedUrl(resolvedLocale, url),
  };
}

export function buildSoftwareApplicationStructuredData({
  locale,
  path,
  title,
  description,
  applicationCategory,
  operatingSystems,
  featureList = [],
  offers = [],
  downloadPath,
}: StructuredDataBase & {
  applicationCategory: string;
  operatingSystems: readonly string[];
  featureList?: readonly string[];
  offers?: readonly StructuredOfferItem[];
  downloadPath?: string;
}): WithContext<SoftwareApplication> {
  const resolvedLocale = resolveSchemaLocale(locale);
  const url = toAbsoluteLocalizedUrl(resolvedLocale, path);
  const downloadUrl = downloadPath
    ? toAbsoluteLocalizedUrl(resolvedLocale, downloadPath)
    : undefined;

  return {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: title,
    applicationCategory,
    description,
    inLanguage: resolvedLocale,
    mainEntityOfPage: url,
    url,
    downloadUrl,
    operatingSystem: operatingSystems.join(', '),
    featureList,
    offers: offers.map((offer) =>
      buildOfferStructuredData({
        locale: resolvedLocale,
        ...offer,
      }),
    ),
    publisher: buildPublisherOrganization(),
  };
}
