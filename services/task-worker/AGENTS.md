# Task Worker - Agent Rules

Rules for AI agents working on the task-worker service. This file supplements CLAUDE.md with the same critical constraints.

## Email Template Rules (MANDATORY)

All email HTML templates live in `src/services/email/templates.py`. **Never** duplicate templates into individual email clients.

### Absolute Rules -- Zero Exceptions

1. **ALL text in `<td>` cells** -- never use `<p>`, `<h1>`-`<h6>`, `<div>` for text
2. **ALL layout via `<table role="presentation">`** -- never use `<div>` for structure
3. **ALL spacing via `padding` on `<td>`** -- never use `margin` on any element
4. **ALL colors in hex** -- never use `rgba()`, `hsla()`, or named colors
5. **`font-family` on every text element** -- repeat it on every `<td>` and `<a>` (inheritance breaks)
6. **`bgcolor` HTML attribute alongside `background-color`** -- for Outlook compatibility
7. **`<body>` is unreliable** -- most clients replace it with `<div>` or strip entirely
8. **Outer `<table>` duplicates ALL body styles** -- `bgcolor`, `background-color`, `-webkit-text-size-adjust`, `-ms-text-size-adjust`
9. **`border="0"` on every `<table>`** -- some clients add visible borders
10. **`width` HTML attr ONLY on `<table>`** -- never on `<body>`, `<span>`, `<div>`, `<p>`, `<img>`
11. **`max-width` CSS ONLY on `<table>`** -- Outlook only supports on tables; some clients don't support at all
12. **Content table dual-width**: `width="600"` HTML attr + `style="width: 100%; max-width: 600px;"` (CSS for responsive, HTML attr as fallback)
13. **MSO ghost table** wraps content for Outlook fixed-width -- `<!--[if mso]>...<![endif]-->`

### CSS Properties -- ALLOWED

| Property | Notes |
|----------|-------|
| `background-color` | Always pair with `bgcolor` HTML attr |
| `color` | Hex only (`#00ffff`) |
| `font-size` | px values only |
| `font-weight` | Keyword `bold` only (not `700`) |
| `font-family` | Web-safe stacks, repeat on every element |
| `line-height` | px only, always add `mso-line-height-rule: exactly` |
| `padding` | On `<td>` only |
| `border`, `border-top`, `border-bottom` | On `<table>` and `<td>` only, solid hex colors |
| `text-align` | On `<td>` elements |
| `text-decoration: none` | On `<a>` tags only. **NEVER `overline`** (Outlook strips). Only `none` is universally safe |
| `width`, `max-width` | On `<table>` elements ONLY. Content table: `width="600"` + `style="width: 100%; max-width: 600px;"` |
| `word-wrap: break-word` | Safe for long URLs |

### CSS Properties -- BANNED

| Property | Reason | Use Instead |
|----------|--------|-------------|
| `margin` | Inconsistent across all clients | `padding` on `<td>` |
| `letter-spacing` | Buggy in Outlook, Gmail, Yahoo | Remove |
| `word-break` | **CRITICAL** -- broken in most clients | `word-wrap: break-word` |
| `display` (except `none`) | Outlook only supports `display: none` | Table structure |
| `linear-gradient()` | Outlook strips it | Solid `background-color` |
| `text-shadow` | Gmail strips entire style attr | Remove |
| `rgba()` / `hsla()` | Gmail strips style block | Hex colors |
| `border-radius` | Outlook ignores | Accept square corners |
| `width` on non-table elements | Not supported on body/span/div/p/img (Outlook, Gmail, Yahoo) | `width` HTML attr on `<table>` only |
| `max-width` on non-table | Outlook ignores on div/span | `<table width="N">` + `style="width: 100%; max-width: Npx"` |
| `height` on body/span/div/p | Not supported | `padding` on `<td>` |
| `text-decoration: overline` | Outlook strips overline | Only use `text-decoration: none` |
| `background-image` inline | Gmail strips if `url()` present | VML or omit |
| `@media` queries | Unreliable | Fixed 600px layout |

### Banned HTML Tags in Email

| Tag | Use Instead |
|-----|-------------|
| `<div>` | `<table>` + `<td>` |
| `<p>` | `<td>` with padding |
| `<h1>` - `<h6>` | `<td>` with font-size/font-weight |
| `<img>` without `width`/`height` attrs | Always set both HTML attributes |

### Bulletproof Button

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

**NO `display: block`** on `<a>` -- Outlook ignores most display values.

### Spacer Pattern

```html
<tr>
    <td style="padding: 15px 0 0 0; font-size: 1px; mso-line-height-rule: exactly; line-height: 1px;">&nbsp;</td>
</tr>
```

### Design Tokens

| Token | Value | Usage |
|-------|-------|-------|
| bg-body | `#0a0a0a` | Email body background |
| bg-card | `#111111` | Main content card |
| bg-code | `#0d0d0d` | OTP code box background |
| accent-green | `#00ff88` | Borders, button, URLs |
| accent-cyan | `#00ffff` | Logo, OTP code text |
| accent-red | `#ff6b6b` | Expiry warning, DEV banner |
| text-primary | `#ffffff` | Headings |
| text-secondary | `#cccccc` | Body text |
| text-muted | `#888888` | Hints |
| text-dim | `#666666` | Disclaimers |
| text-footer | `#555555` | Copyright |
| border-accent | `#00ff88` | Card border, OTP box |
| border-subtle | `#333333` | Footer separator |

### Template Architecture

```
src/services/email/
  templates.py          # SINGLE SOURCE OF TRUTH for all HTML
  resend_client.py      # Resend API -- calls templates.render_*()
  brevo_client.py       # Brevo API -- calls templates.render_*()
  smtp_client.py        # SMTP/Mailpit -- calls templates.render_*(dev_banner=True)
```

- `render_otp_template(code, expires_in, locale, *, dev_banner=False)`
- `render_magic_link_template(url, expires_in, locale, otp_code, *, dev_banner=False)`
- Future templates: add to `templates.py`, never inline HTML in client files

### Pre-Commit Checklist for Email Templates

Before committing any email template change, verify:

- [ ] No `<div>`, `<p>`, `<h1>`-`<h6>` tags
- [ ] No `margin` property anywhere
- [ ] No `letter-spacing` property
- [ ] No `word-break` property
- [ ] No `display: block` or `display: inline-block`
- [ ] No `rgba()` or `linear-gradient()`
- [ ] No `text-shadow`
- [ ] No `text-decoration: overline` (only `none` is safe)
- [ ] No `width` on non-table elements (body/span/div/p/img)
- [ ] No `max-width` on non-table elements
- [ ] All `line-height` values in px with `mso-line-height-rule: exactly`
- [ ] All `background-color` paired with `bgcolor` HTML attr
- [ ] `<body>` has `bgcolor` HTML attribute (clients replace body with div)
- [ ] Outer `<table>` duplicates ALL body styles: `bgcolor`, `background-color`, `-webkit-text-size-adjust`, `-ms-text-size-adjust`
- [ ] Content table uses `width="600"` + `style="width: 100%; max-width: 600px;"`
- [ ] `font-family` on every `<td>` and `<a>` with text
- [ ] MSO ghost table around 600px container
- [ ] VML button in `<!--[if mso]>` conditional
- [ ] Outer `<table>` duplicates body styles (bgcolor, background-color, width="100%")

## TaskIQ Patterns

- **Message format**: `{"task_id": "...", "task_name": "...", "labels": {}, "args": [...], "kwargs": {}}`
- **Broker**: Redis Streams via `redis.xadd("taskiq", {"data": message_bytes})`
- **Task decorator**: `@broker.task(task_name="...", queue="...", retry_policy="...")`
- **`with_labels` deprecated**: Set labels in decorator, not via `.with_labels()`
- **Import tasks at module end** in `broker.py` to register them
