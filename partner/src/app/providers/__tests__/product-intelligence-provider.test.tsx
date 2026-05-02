// @vitest-environment node

import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import {
  ProductIntelligenceProvider,
  useProductFeatureFlag,
} from '@/app/providers/product-intelligence-provider';
import { buildDefaultFeatureFlagBootstrap } from '@/lib/product-intelligence/contracts';

describe('ProductIntelligenceProvider', () => {
  it('exposes deterministic default-off fallback values through the typed hook', () => {
    const bootstrap = buildDefaultFeatureFlagBootstrap('user_42', 'fallback');
    function FlagSnapshot() {
      const value = useProductFeatureFlag('partner_portal_realtime_workspace_feed_v1');
      return <pre>{JSON.stringify(value)}</pre>;
    }

    const html = renderToStaticMarkup(
      <ProductIntelligenceProvider bootstrap={bootstrap}>
        <FlagSnapshot />
      </ProductIntelligenceProvider>,
    );

    expect(html).toContain('&quot;distinctId&quot;:&quot;user_42&quot;');
    expect(html).toContain('&quot;evaluationSource&quot;:&quot;fallback&quot;');
    expect(html).toContain('&quot;fallbackUsed&quot;:true');
    expect(html).toContain('&quot;key&quot;:&quot;partner_portal_realtime_workspace_feed_v1&quot;');
    expect(html).toContain('&quot;value&quot;:false');
  });
});
