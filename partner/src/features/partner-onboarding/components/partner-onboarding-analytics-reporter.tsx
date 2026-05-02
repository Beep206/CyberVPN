'use client';

import { useLocale } from 'next-intl';
import { usePathname } from 'next/navigation';
import { useEffect, useEffectEvent, useRef } from 'react';
import { sendProductAnalyticsEvent } from '@/lib/product-intelligence/client';
import {
  buildOnboardingStartedCapture,
  buildOnboardingStepCompletedCapture,
} from '@/lib/product-intelligence/event-builders';

type OnboardingStageKey = 'workspace' | 'profile' | 'compliance' | 'review';

export function PartnerOnboardingAnalyticsReporter({
  applicationStatus,
  distinctId,
  stageProgress,
  workspaceStatus,
}: {
  applicationStatus: string;
  distinctId: string | null;
  stageProgress: Record<OnboardingStageKey, boolean>;
  workspaceStatus: string;
}) {
  const locale = useLocale();
  const pathname = usePathname();
  const startedKeyRef = useRef('');
  const completedStagesRef = useRef<Set<string>>(new Set());

  const reportStarted = useEffectEvent((nextDistinctId: string | null, nextPathname: string) => {
    if (
      !nextDistinctId
      || !nextPathname
      || (applicationStatus === 'unknown' && workspaceStatus === 'unknown')
    ) {
      return;
    }

    const startedKey = `${nextDistinctId}:${nextPathname}:onboarding_started`;
    if (startedKeyRef.current === startedKey) {
      return;
    }

    startedKeyRef.current = startedKey;
    sendProductAnalyticsEvent(buildOnboardingStartedCapture({
      applicationStatus,
      distinctId: nextDistinctId,
      locale,
      path: nextPathname,
      workspaceStatus,
    }));
  });

  const reportCompletedStages = useEffectEvent((nextDistinctId: string | null, nextPathname: string) => {
    if (!nextDistinctId || !nextPathname) {
      return;
    }

    (Object.entries(stageProgress) as Array<[OnboardingStageKey, boolean]>).forEach(([stage, completed]) => {
      if (!completed) {
        return;
      }

      const stageKey = `${nextDistinctId}:${nextPathname}:${stage}`;
      if (completedStagesRef.current.has(stageKey)) {
        return;
      }

      completedStagesRef.current.add(stageKey);
      sendProductAnalyticsEvent(buildOnboardingStepCompletedCapture({
        applicationStatus,
        distinctId: nextDistinctId,
        locale,
        path: nextPathname,
        stage,
        workspaceStatus,
      }));
    });
  });

  useEffect(() => {
    reportStarted(distinctId, pathname);
    reportCompletedStages(distinctId, pathname);
  }, [distinctId, pathname, stageProgress, applicationStatus, workspaceStatus]);

  return null;
}
