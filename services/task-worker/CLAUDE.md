# Task Worker - Coding Rules

Background job worker service for CyberVPN. Processes email delivery, scheduled tasks, and async jobs via TaskIQ + Redis Streams.

## Stack

| Library | Purpose |
|---------|---------|
| Python 3.13 | Runtime |
| TaskIQ | Job broker (Redis Streams) |
| httpx | Async HTTP (Resend, Brevo APIs) |
| smtplib | SMTP (Mailpit dev mode) |
| redis | Cache + round-robin counter |
| structlog | Structured logging |

## Email Template Rules

**MANDATORY**: All email HTML templates live in `src/services/email/templates.py`. Never duplicate templates into individual email clients.

### Email Client Compatibility Checklist

Every email template MUST follow these rules for cross-client rendering:

#### Layout
- **Table-based layout only** -- use `<table role="presentation">` for ALL structural elements
- **NEVER use `<div>` for layout** -- only `<span>` for inline text wrapping
- **NEVER use `<p>`, `<h1>`-`<h6>` tags** -- ALL text goes in `<td>` cells. These tags have inconsistent `margin` rendering across email clients (Outlook adds extra spacing)
- **Set `border="0"` on every `<table>`** -- some clients add visible borders by default
- **Use `align="center"` on `<table>`** instead of `margin: 0 auto` on `<div>`
- **Spacing via `padding` on `<td>` ONLY** -- never use `margin` on any element

#### Width & Max-Width
- **`width` HTML attribute ONLY on `<table>` elements** -- not on `<body>`, `<span>`, `<div>`, `<p>`, `<img>` (Outlook, Gmail, Yahoo, ProtonMail strip or ignore)
- **`max-width` CSS ONLY on `<table>` elements** -- Outlook only supports on tables; Yahoo/AOL/ProtonMail don't support on tables per CSS 2.1 spec (graceful degradation)
- **Content table dual-width pattern**: set `width="600"` HTML attr AND `style="width: 100%; max-width: 600px;"`. Modern clients use CSS (responsive), old clients fall back to HTML attr (600px fixed)
- **MSO ghost table** wraps content for Outlook fixed-width:
  ```html
  <!--[if mso]>
  <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" align="center"><tr><td>
  <![endif]-->
  <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0"
      style="width: 100%; max-width: 600px; ...">
    ...content...
  </table>
  <!--[if mso]>
  </td></tr></table>
  <![endif]-->
  ```
- **LaPoste.net bug**: sets `table { width:inherit; }` -- no workaround, accept degradation

#### CSS Properties -- ALLOWED
- `background-color` (always pair with `bgcolor` HTML attribute)
- `color` (hex only, e.g. `#00ffff` -- never `rgba()` or named colors)
- `font-size` (px values only)
- `font-weight` (keyword `bold` only -- numeric values like `700` fail in some clients)
- `font-family` (web-safe stacks only, repeat on every `<td>` that has text)
- `line-height` (px values ONLY, always pair with `mso-line-height-rule: exactly`)
- `padding` on `<td>` elements only (longhand preferred: `padding: 20px 40px`)
- `border` and `border-bottom`/`border-top` on `<table>` and `<td>` only (solid hex colors only)
- `text-align` on `<td>` elements
- `text-decoration: none` on `<a>` tags only (**NEVER use `overline`** -- Outlook strips it; `underline` and `line-through` have partial support; only `none` is universally safe)
- `width` and `max-width` on `<table>` elements ONLY (see Width & Max-Width section above)
- `word-wrap: break-word` (safe fallback for long URLs)

#### CSS Properties -- BANNED

| Property | Reason | Alternative |
|----------|--------|-------------|
| `margin` | Inconsistent on all elements across clients (Outlook, Gmail) | Use `padding` on `<td>` |
| `letter-spacing` | Buggy in Outlook, Gmail, Yahoo, AOL | Remove -- rely on `font-size` |
| `word-break` | **CRITICAL** -- broken in Gmail, Outlook, Yahoo, most clients | Use `word-wrap: break-word` |
| `display` (except `none`) | Outlook only supports `display: none` | Use table structure |
| `linear-gradient()` | Outlook strips it | Solid `background-color` |
| `text-shadow` | Gmail strips entire style attribute | Remove |
| `rgba()` | Gmail strips entire `<style>` block | Use hex colors |
| `border-radius` | Outlook ignores, square corners | Accept graceful degradation |
| `width` on non-table elements | Not supported on `<body>`, `<span>`, `<div>`, `<p>`, `<img>` (Outlook, Gmail, Yahoo) | Use `width` HTML attr on `<table>` only |
| `max-width` on non-table elements | Outlook ignores on `<div>`, `<span>`, etc. | Use `<table width="N">` + `style="width: 100%; max-width: Npx"` |
| `height` on `<body>`, `<span>`, `<div>`, `<p>` | Not supported | Use `padding` on `<td>` for vertical space |
| `text-decoration: overline` | Outlook strips `overline` value | Only use `text-decoration: none` |
| `<div>` for structure | Replaced/stripped by webmail clients | Use `<table>` |
| `<p>`, `<h1>`-`<h6>` | Margin rendering differs wildly | Use `<td>` with font styling |
| `background-image` in inline styles | Gmail strips style attribute if `url()` present | Omit or use VML for Outlook |
| `@media` queries | Unreliable across clients | Fixed-width 600px layout |

#### Bulletproof Button Pattern
```html
<table role="presentation" align="center" cellspacing="0" cellpadding="0" border="0">
    <tr>
        <!--[if mso]>
        <td align="center" bgcolor="#00ff88" style="padding: 0;">
            <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
                xmlns:w="urn:schemas-microsoft-com:office:word"
                href="URL"
                style="height:52px;v-text-anchor:middle;width:240px;"
                fillcolor="#00ff88" stroke="f">
            <w:anchorlock/>
            <center style="color:#0a0a0a;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;font-size:18px;font-weight:bold;">LABEL</center>
            </v:roundrect>
        </td>
        <![endif]-->
        <!--[if !mso]><!-->
        <td align="center" bgcolor="#00ff88" style="background-color: #00ff88; padding: 16px 48px;">
            <a href="URL" style="color: #0a0a0a; font-size: 18px; font-weight: bold; text-decoration: none; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
                LABEL
            </a>
        </td>
        <!--<![endif]-->
    </tr>
</table>
```

**Key points:**
- VML `<v:roundrect>` in its own `<td>` with `<!--[if mso]>` conditional
- Non-MSO `<td>` wrapped in `<!--[if !mso]><!--> ... <!--<![endif]-->`
- **NO `display: block`** on `<a>` tag (Outlook ignores most `display` values)
- `font-family` repeated on `<a>` tag (inheritance breaks in some clients)

#### Spacing
- Use `padding` on `<td>` for all spacing
- For standalone spacers between sections:
  ```html
  <tr>
      <td style="padding: 15px 0 0 0; font-size: 1px; mso-line-height-rule: exactly; line-height: 1px;">&nbsp;</td>
  </tr>
  ```
- **NEVER use `margin`** -- not even on `<body>` (except `margin: 0` reset)

#### Body Tag -- CRITICAL: `<body>` Is Unreliable

Most email clients **replace `<body>` with a `<div>`** or strip it entirely:
- **Replace with `<div>`** (partial support): Gmail, Yahoo, AOL, Orange, Outlook.com, HEY
- **Strip/ignore entirely** (no support): GMX, WEB.DE, 1&1, SFR, ProtonMail, LaPoste, Mail.ru, Fastmail, Samsung Email, Apple Mail, Outlook Windows, Outlook macOS, Thunderbird

**Defense: outer `<table>` is the true layout root.** It must duplicate ALL body styles:

```html
<body bgcolor="#0a0a0a" style="margin: 0; padding: 0; background-color: #0a0a0a; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
    <!-- This table IS the real body -- survives body replacement/stripping -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
        bgcolor="#0a0a0a"
        style="background-color: #0a0a0a; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
```

Checklist:
- `bgcolor` HTML attribute on BOTH `<body>` AND outer `<table>`
- `background-color` CSS on BOTH `<body>` AND outer `<table>`
- `-webkit-text-size-adjust: 100%` on BOTH `<body>` AND outer `<table>`
- `-ms-text-size-adjust: 100%` on BOTH `<body>` AND outer `<table>`
- `margin: 0; padding: 0` on `<body>` (lost when replaced, but harmless)
- `width="100%"` HTML attr on outer `<table>`

#### Font Stack
- Display: `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif`
- Monospace (OTP codes): `'Courier New', Courier, monospace`
- Repeat `font-family` on every `<td>` and `<a>` that has text (inheritance breaks in some clients)

### CyberVPN Design Tokens (Email)

| Token | Value | Usage |
|-------|-------|-------|
| bg-body | `#0a0a0a` | Email body background |
| bg-card | `#111111` | Main content card |
| bg-code | `#0d0d0d` | OTP code box background |
| accent-green | `#00ff88` | Borders, links, URLs |
| accent-cyan | `#00ffff` | Logo, OTP code text |
| accent-red | `#ff6b6b` | Expiration warnings, DEV banner |
| text-primary | `#ffffff` | Headings |
| text-secondary | `#cccccc` | Body text |
| text-muted | `#888888` | Hints, secondary info |
| text-dim | `#666666` | Disclaimers |
| text-footer | `#555555` | Copyright |
| border-accent | `#00ff88` | Card border, OTP box border |
| border-subtle | `#333333` | Footer separator |

### Template Architecture

```
src/services/email/
  templates.py          # SINGLE SOURCE OF TRUTH for all HTML templates
  resend_client.py      # Resend API -- calls templates.render_*()
  brevo_client.py       # Brevo API -- calls templates.render_*()
  smtp_client.py        # SMTP/Mailpit -- calls templates.render_*(dev_banner=True)
```

- `render_otp_template(code, expires_in, locale, *, dev_banner=False)` -- OTP verification email
- `render_magic_link_template(url, expires_in, locale, otp_code, *, dev_banner=False)` -- Magic link email
- Future templates: add to `templates.py`, never inline HTML in client files

### Testing Email Changes

1. Rebuild worker: `cd infra && docker compose build cybervpn-worker && docker compose up -d cybervpn-worker`
2. Trigger email via API (register or magic-link)
3. Check Mailpit UI at `http://localhost:8025/mailpit-1/`, `/mailpit-2/`, `/mailpit-3/`
4. Verify HTML rendering in the Mailpit preview tab
5. For production email client testing, use [Litmus](https://litmus.com) or [Email on Acid](https://emailonacid.com)

## TaskIQ Patterns

- **Message format**: `{"task_id": "...", "task_name": "...", "labels": {}, "args": [...], "kwargs": {}}`
- **Broker**: Redis Streams via `redis.xadd("taskiq", {"data": message_bytes})`
- **Task decorator**: `@broker.task(task_name="...", queue="...", retry_policy="...")`
- **`with_labels` deprecated**: Set labels in decorator, not via `.with_labels()`
- **Import tasks at module end** in `broker.py` to register them
