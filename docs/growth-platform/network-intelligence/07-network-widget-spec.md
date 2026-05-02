# Network Widget Spec

## Purpose

Allow CyberVPN and approved partners to embed public network proof in external pages without exposing raw internal data.

## Widget Types

- iframe widget
- badge widget
- uptime badge
- speed badge
- branded network card

## Widget Requirements

- sanitized data only;
- cache-friendly responses;
- low-latency embeds;
- optional partner branding within approved limits.

## Embed Example

```html
<iframe
  src="https://cybervpn.com/widgets/network?partner=partner_slug"
  loading="lazy"
></iframe>
```

## Configuration Options

- locale
- theme variant
- region focus
- widget size
- partner identifier where allowed

## Cache and Rate Limits

- widget payload should be backed by public snapshot cache;
- partner widget traffic should be rate limited and observable;
- embed abuse should be detectable.

## Security

- no partner-private data;
- no raw infrastructure identifiers;
- signed or validated branding parameters where needed.

## Customization

Allowed:

- theme variant
- locale
- selected approved widgets

Not allowed:

- arbitrary metric injection
- unsupported branding assets
- unsafe or misleading copy overrides
