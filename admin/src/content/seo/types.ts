import type { StructuredOfferItem } from '@/shared/lib/structured-data';

export type SeoCallToAction = {
  label: string;
  href: string;
  description: string;
  seoCta: string;
  seoZone: string;
};

export type SeoResourceLink = {
  label: string;
  href: string;
  description: string;
};

export type SeoArticleSection = {
  title: string;
  paragraphs: readonly string[];
  bullets?: readonly string[];
};

export type SeoHubCard = {
  slug: string;
  path: string;
  eyebrow: string;
  title: string;
  description: string;
  stats: readonly string[];
};

export type SeoHubContent = {
  path: string;
  badge: string;
  title: string;
  description: string;
  bullets: readonly string[];
  proofPoints: readonly string[];
  cards: readonly SeoHubCard[];
  ctaLinks: readonly SeoCallToAction[];
};

export type SeoArticleEntry = {
  slug: string;
  path: string;
  badge: string;
  title: string;
  description: string;
  readingTime: string;
  updatedAt: string;
  heroPoints: readonly string[];
  sections: readonly SeoArticleSection[];
  relatedLinks: readonly SeoResourceLink[];
  ctaLinks: readonly SeoCallToAction[];
};

export type SeoStaticKnowledgePage = Omit<SeoArticleEntry, 'slug'>;

export type SeoDeviceEntry = SeoArticleEntry & {
  applicationCategory: string;
  operatingSystems: readonly string[];
  featureList: readonly string[];
  downloadPath: string;
  offers: readonly StructuredOfferItem[];
};
