import type { ProductAnalyticsCaptureInput } from './contracts';

type CheckoutCaptureBase = {
  distinctId: string;
  locale: string;
  path: string;
  storefrontKey: string;
};

type CheckoutStartedInput = CheckoutCaptureBase & {
  pricebookKey: string | null;
  saleChannel: string;
};

type CheckoutPaymentSubmittedInput = CheckoutCaptureBase & {
  currencyCode: string;
  flow: 'new_purchase';
  offerKey: string;
  pricebookKey: string;
  saleChannel: string;
};

type CheckoutStepInput = CheckoutCaptureBase & {
  step: 'catalog' | 'order_ready';
};

type OnboardingCaptureBase = {
  applicationStatus: string;
  distinctId: string;
  locale: string;
  path: string;
  workspaceStatus: string;
};

type OnboardingStepCompletedInput = OnboardingCaptureBase & {
  stage: 'workspace' | 'profile' | 'compliance' | 'review';
};

export function buildCheckoutStartedCapture(input: CheckoutStartedInput): ProductAnalyticsCaptureInput {
  return {
    distinctId: input.distinctId,
    event: 'checkout_started',
    properties: {
      checkout_surface: 'storefront',
      locale: input.locale,
      path: input.path,
      pricebook_key: input.pricebookKey,
      route_group: 'storefront_checkout',
      sale_channel: input.saleChannel,
      storefront_key: input.storefrontKey,
    },
  };
}

export function buildCheckoutStepViewedCapture(input: CheckoutStepInput): ProductAnalyticsCaptureInput {
  return {
    distinctId: input.distinctId,
    event: 'checkout_step_viewed',
    properties: {
      checkout_surface: 'storefront',
      locale: input.locale,
      path: input.path,
      route_group: 'storefront_checkout',
      step: input.step,
      storefront_key: input.storefrontKey,
    },
  };
}

export function buildCheckoutStepCompletedCapture(input: CheckoutStepInput): ProductAnalyticsCaptureInput {
  return {
    distinctId: input.distinctId,
    event: 'checkout_step_completed',
    properties: {
      checkout_surface: 'storefront',
      locale: input.locale,
      path: input.path,
      route_group: 'storefront_checkout',
      step: input.step,
      storefront_key: input.storefrontKey,
    },
  };
}

export function buildCheckoutPaymentSubmittedCapture(
  input: CheckoutPaymentSubmittedInput,
): ProductAnalyticsCaptureInput {
  return {
    distinctId: input.distinctId,
    event: 'checkout_payment_submitted',
    properties: {
      checkout_surface: 'storefront',
      currency_code: input.currencyCode,
      flow: input.flow,
      locale: input.locale,
      offer_key: input.offerKey,
      path: input.path,
      pricebook_key: input.pricebookKey,
      route_group: 'storefront_checkout',
      sale_channel: input.saleChannel,
      storefront_key: input.storefrontKey,
    },
  };
}

export function buildOnboardingStartedCapture(input: OnboardingCaptureBase): ProductAnalyticsCaptureInput {
  return {
    distinctId: input.distinctId,
    event: 'onboarding_started',
    properties: {
      application_status: input.applicationStatus,
      locale: input.locale,
      path: input.path,
      route_group: 'application_onboarding',
      surface: 'partner_portal',
      workspace_status: input.workspaceStatus,
    },
  };
}

export function buildOnboardingStepCompletedCapture(
  input: OnboardingStepCompletedInput,
): ProductAnalyticsCaptureInput {
  return {
    distinctId: input.distinctId,
    event: 'onboarding_step_completed',
    properties: {
      application_status: input.applicationStatus,
      locale: input.locale,
      path: input.path,
      route_group: 'application_onboarding',
      stage: input.stage,
      surface: 'partner_portal',
      workspace_status: input.workspaceStatus,
    },
  };
}
