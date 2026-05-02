'use client';

import { createContext, useContext } from 'react';
import {
  buildDefaultFeatureFlagBootstrap,
  type ProductFeatureFlagBootstrap,
  type ProductFeatureFlagKey,
} from '@/lib/product-intelligence/contracts';

const ProductIntelligenceContext = createContext<ProductFeatureFlagBootstrap>(
  buildDefaultFeatureFlagBootstrap(),
);

export function ProductIntelligenceProvider({
  bootstrap,
  children,
}: {
  bootstrap: ProductFeatureFlagBootstrap;
  children: React.ReactNode;
}) {
  return (
    <ProductIntelligenceContext.Provider value={bootstrap}>
      {children}
    </ProductIntelligenceContext.Provider>
  );
}

export function useProductIntelligenceBootstrap(): ProductFeatureFlagBootstrap {
  return useContext(ProductIntelligenceContext);
}

export function useProductFeatureFlag(flagKey: ProductFeatureFlagKey) {
  const bootstrap = useProductIntelligenceBootstrap();

  return {
    distinctId: bootstrap.distinctId,
    evaluationSource: bootstrap.evaluationSource,
    fallbackUsed: bootstrap.evaluationSource !== 'server_evaluated',
    key: flagKey,
    value: bootstrap.flags[flagKey],
  };
}
