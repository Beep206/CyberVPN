# Public Speed Map Product Spec

## Product Goal

Create a public, trustworthy, and conversion-aware network proof surface.

## Core Pages

- `/[locale]/network`
- `/[locale]/status`
- `/[locale]/network/regions`
- `/[locale]/network/regions/:country`
- `/[locale]/network/dpi-resistance`
- `/[locale]/network/uptime`

## Core Blocks

- global health summary
- freshness display
- region leaderboard
- region cards
- public incident block
- uptime history
- methodology note
- CTA into Mini App

## UX Requirements

- SSR-friendly initial render;
- last updated and freshness state always visible;
- live-looking visuals must still be honest about data freshness;
- degraded and stale state must be explicit.

## Conversion Path

Primary CTA path:

- public page -> Mini App -> trial or purchase

Secondary path:

- public page -> web/storefront for users outside Telegram

## Region Cards

Each region card should show:

- public region name;
- latency;
- speed;
- uptime;
- current status;
- confidence where applicable.

## Incident Block

Must show:

- current incident severity;
- public summary;
- affected regions;
- current state;
- timestamps.

## Methodology Block

Should explain:

- what metrics are shown;
- how fresh they are;
- what is aggregated;
- what is intentionally not public.

## SEO Blocks

Include:

- static context around network quality;
- localized explanatory copy;
- internal links to region and uptime pages.
