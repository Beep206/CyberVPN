'use client';

import { AxiosError } from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@/i18n/navigation';
import { authApi } from '@/lib/api/auth';
import { storefrontApi } from '@/lib/api/storefront';
import { buildInternalLoginHref } from '@/features/auth/lib/session';
import type { StorefrontSurfaceContext } from '@/features/storefront-shell/lib/runtime';

type StorefrontLegalLabels = {
  eyebrow: string;
  title: string;
  subtitle: string;
  required: string;
  optional: string;
  checkoutCta: string;
  supportCta: string;
  loading: string;
  empty: string;
};

export function StorefrontLegalDocumentsShell({
  surfaceContext,
  locale,
  labels,
}: {
  surfaceContext: StorefrontSurfaceContext;
  locale: string;
  labels: StorefrontLegalLabels;
}) {
  const queryClient = useQueryClient();
  const legalSetQuery = useQuery({
    queryKey: ['storefront', surfaceContext.storefrontKey, 'legal-set'],
    queryFn: async () => {
      const response = await storefrontApi.resolveLegalDocumentSet({
        storefront_key: surfaceContext.storefrontKey,
      });
      return response.data;
    },
  });

  const legalDocumentsQuery = useQuery({
    queryKey: ['storefront', surfaceContext.storefrontKey, 'legal-documents', locale],
    queryFn: async () => {
      const response = await storefrontApi.listLegalDocuments({ locale });
      return response.data;
    },
  });

  const sessionQuery = useQuery({
    queryKey: ['storefront', surfaceContext.storefrontKey, 'customer-session'],
    queryFn: async () => {
      try {
        const response = await authApi.session();
        return response.data;
      } catch (error) {
        if (error instanceof AxiosError && error.response?.status === 401) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
  });

  const acceptancesQuery = useQuery({
    queryKey: ['storefront', surfaceContext.storefrontKey, 'policy-acceptance', 'me'],
    queryFn: async () => {
      const response = await storefrontApi.listMyPolicyAcceptance();
      return response.data;
    },
    enabled: Boolean(sessionQuery.data),
    retry: false,
  });

  const createAcceptanceMutation = useMutation({
    mutationFn: async () => {
      const legalSet = legalSetQuery.data;
      if (!legalSet) {
        throw new Error('Legal document set is not available for this storefront.');
      }

      const response = await storefrontApi.createPolicyAcceptance({
        legal_document_set_id: legalSet.id,
        storefront_id: legalSet.storefront_id,
        acceptance_channel: 'storefront_legal_surface',
        device_context: {
          locale,
          surface_family: 'storefront',
          storefront_key: surfaceContext.storefrontKey,
          support_profile_email: surfaceContext.supportProfile.email,
          communication_sender_email: surfaceContext.communicationProfile.senderEmail,
        },
      });
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ['storefront', surfaceContext.storefrontKey, 'policy-acceptance', 'me'],
      });
    },
  });

  const legalSet = legalSetQuery.data;
  const legalDocumentsById = new Map((legalDocumentsQuery.data ?? []).map((document) => [document.id, document]));
  const documents = legalSet
    ? legalSet.documents
      .map((item) => ({
        item,
        document: legalDocumentsById.get(item.legal_document_id),
      }))
      .filter((entry) => entry.document)
      .sort((left, right) => left.item.display_order - right.item.display_order)
    : [];
  const currentAcceptance = acceptancesQuery.data?.find((acceptance) => acceptance.legal_document_set_id === legalSet?.id) ?? null;
  const requiresSignIn = !sessionQuery.isLoading && !sessionQuery.data;
  const loginHref = buildInternalLoginHref(surfaceContext.routes.legal, locale);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8 md:px-6 md:py-10">
      <section className="rounded-[2rem] border border-grid-line/20 bg-terminal-surface/45 p-6 shadow-[0_0_32px_rgba(0,255,255,0.06)] backdrop-blur md:p-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan">{labels.eyebrow}</p>
        <h1 className="mt-3 text-3xl font-display font-black uppercase tracking-[0.1em] text-foreground md:text-4xl">
          {labels.title}
        </h1>
        <p className="mt-3 max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
          {labels.subtitle.replace('{setName}', legalSet?.display_name ?? surfaceContext.storefrontKey)}
        </p>
      </section>

      {legalSetQuery.isLoading || legalDocumentsQuery.isLoading ? (
        <section className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 font-mono text-sm text-muted-foreground">
          {labels.loading}
        </section>
      ) : null}

      {!legalSetQuery.isLoading && !legalDocumentsQuery.isLoading && documents.length === 0 ? (
        <section className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 font-mono text-sm text-muted-foreground">
          {labels.empty}
        </section>
      ) : null}

      <section className="grid gap-4 md:grid-cols-[1.15fr_0.85fr]">
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Legal acceptance routing
          </p>
          <h2 className="mt-3 font-display text-xl text-foreground">
            {currentAcceptance ? 'Acceptance recorded for this storefront realm.' : 'Customer acceptance stays bound to this storefront and customer realm.'}
          </h2>
          <div className="mt-4 space-y-2 font-mono text-sm text-muted-foreground">
            <p>Storefront support and legal acceptance stay on the branded customer surface.</p>
            <p>Partner operator contracts and compliance follow-up stay on the workspace portal, not on storefront customer messaging.</p>
            {legalSet ? (
              <p>Resolved legal set: {legalSet.display_name} · {legalSet.set_key}</p>
            ) : null}
            {currentAcceptance ? (
              <p>
                Accepted at {new Date(currentAcceptance.accepted_at).toLocaleString(locale)} via {currentAcceptance.acceptance_channel}.
              </p>
            ) : null}
          </div>
        </article>

        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/60 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan">Acceptance control</p>
          {sessionQuery.isLoading ? (
            <p className="mt-4 font-mono text-sm text-muted-foreground">Resolving customer session…</p>
          ) : null}
          {requiresSignIn ? (
            <div className="mt-4 space-y-4">
              <p className="font-mono text-sm leading-6 text-muted-foreground">
                Sign in with the customer storefront identity before accepting the active legal set. Partner operator sessions stay isolated on portal hosts.
              </p>
              <Link
                href={loginHref}
                className="inline-flex items-center justify-center rounded-lg bg-neon-cyan px-4 py-3 font-mono text-sm font-bold uppercase tracking-[0.18em] text-black transition-colors hover:bg-neon-cyan/90"
              >
                Customer sign in
              </Link>
            </div>
          ) : null}
          {!requiresSignIn && !currentAcceptance ? (
            <div className="mt-4 space-y-4">
              <p className="font-mono text-sm leading-6 text-muted-foreground">
                Accept the current required legal set before continuing with branded checkout on this storefront.
              </p>
              <button
                type="button"
                onClick={() => void createAcceptanceMutation.mutateAsync()}
                disabled={!legalSet || createAcceptanceMutation.isPending}
                className="inline-flex items-center justify-center rounded-lg bg-neon-cyan px-4 py-3 font-mono text-sm font-bold uppercase tracking-[0.18em] text-black transition-colors hover:bg-neon-cyan/90 disabled:cursor-not-allowed disabled:bg-neon-cyan/50"
              >
                {createAcceptanceMutation.isPending ? 'Recording acceptance…' : 'Accept required documents'}
              </button>
              {createAcceptanceMutation.isError ? (
                <p className="font-mono text-xs text-warning">
                  {createAcceptanceMutation.error instanceof Error
                    ? createAcceptanceMutation.error.message
                    : 'Acceptance could not be recorded for this storefront.'}
                </p>
              ) : null}
            </div>
          ) : null}
          {currentAcceptance ? (
            <div className="mt-4 space-y-3">
              <p className="font-mono text-sm leading-6 text-muted-foreground">
                Acceptance is already attached to the current customer principal and storefront realm.
              </p>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-matrix-green">
                Accepted
              </p>
            </div>
          ) : null}
        </article>
      </section>

      <section className="grid gap-4">
        {documents.map(({ item, document }) => (
          <article
            key={item.id}
            className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display text-xl text-foreground">{document?.title}</h2>
              <span className="rounded-full border border-grid-line/25 bg-terminal-bg/60 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                {item.required ? labels.required : labels.optional}
              </span>
            </div>
            <p className="mt-3 font-mono text-xs text-muted-foreground">
              {document?.document_type} · {document?.locale}
            </p>
            <pre className="mt-4 max-h-72 overflow-auto rounded-xl border border-grid-line/15 bg-terminal-bg/65 p-4 whitespace-pre-wrap font-mono text-xs text-muted-foreground">
              {document?.content_markdown}
            </pre>
          </article>
        ))}
      </section>

      <div className="flex flex-wrap gap-3">
        <Link
          href={surfaceContext.routes.checkout}
          className="inline-flex items-center justify-center rounded-lg bg-neon-cyan px-4 py-3 font-mono text-sm font-bold uppercase tracking-[0.18em] text-black transition-colors hover:bg-neon-cyan/90"
        >
          {labels.checkoutCta}
        </Link>
        <Link
          href={surfaceContext.routes.support}
          className="inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-bg/60 px-4 py-3 font-mono text-sm uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple/40"
        >
          {labels.supportCta}
        </Link>
      </div>
    </div>
  );
}
