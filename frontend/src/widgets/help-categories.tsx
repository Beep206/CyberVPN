import { getTranslations } from 'next-intl/server';
import { HelpCategoriesServer } from '@/widgets/help-categories-server';
import { getHelpKnowledge } from '@/widgets/help-faq-server';

export async function HelpCategories() {
  const t = await getTranslations('HelpCenter');
  const categories = await getHelpKnowledge();

  return (
    <HelpCategoriesServer
      categories={categories}
      title={t('categories_title')}
      intro={t('categories_intro')}
    />
  );
}
