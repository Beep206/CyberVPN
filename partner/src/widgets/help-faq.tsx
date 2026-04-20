import { Suspense } from 'react';
import { getTranslations } from 'next-intl/server';
import {
  HELP_CATEGORY_IDS,
  HelpFaqServer,
  getHelpKnowledge,
} from '@/widgets/help-faq-server';
import { HelpFaqClient } from '@/widgets/help-faq-client';

export async function HelpFaq() {
  const t = await getTranslations('HelpCenter');
  const categories = await getHelpKnowledge();

  return (
    <>
      <Suspense fallback={null}>
        <HelpFaqClient categoryIds={HELP_CATEGORY_IDS} />
      </Suspense>
      <HelpFaqServer
        categories={categories}
        title={t('faq_title')}
        intro={t('faq_intro')}
      />
    </>
  );
}
