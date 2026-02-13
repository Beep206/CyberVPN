"""
Email-compatible HTML templates for CyberVPN transactional emails.

STRICT RULES (see CLAUDE.md + AGENTS.md for full spec):
- Table-based layout ONLY. No <div>, <p>, <h1>-<h6> tags.
- ALL text goes in <td> cells. Spacing via padding on <td>, never margin.
- No CSS: gradient, text-shadow, rgba(), display, word-break, letter-spacing, margin.
- Bulletproof buttons via <table> + VML for Outlook.
- MSO conditional for container width. bgcolor HTML attr alongside background-color.
- line-height in px with mso-line-height-rule:exactly.
- font-family repeated on every <td> that has text.
- width HTML attr ONLY on <table>. CSS width/max-width ONLY on <table>.
- <body> bgcolor attr as fallback (clients may replace <body> with <div>).
- text-decoration: only "none" (overline broken in Outlook).
"""

# -- Shared fragments --------------------------------------------------------

_FONT = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
_MONO = "'Courier New', Courier, monospace"
_BG_BODY = "#0a0a0a"
_BG_CARD = "#111111"
_BG_CODE = "#0d0d0d"
_CYAN = "#00ffff"
_GREEN = "#00ff88"
_RED = "#ff6b6b"
_WHITE = "#ffffff"
_TEXT = "#cccccc"
_MUTED = "#888888"
_DIM = "#666666"
_FOOTER = "#555555"
_BORDER = "#333333"


def render_otp_template(
    code: str,
    expires_in: str,
    locale: str,
    *,
    dev_banner: bool = False,
) -> str:
    """Render email-compatible OTP verification email."""
    banner = _dev_banner_html() if dev_banner else ""
    return f"""\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Verify Your CyberVPN Account</title>
</head>
<body bgcolor="{_BG_BODY}" style="margin: 0; padding: 0; background-color: {_BG_BODY}; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
    <!--
        Outer wrapper table duplicates ALL body styles because many clients
        (Gmail, Yahoo, AOL, Orange, Outlook.com, HEY, GMX, WEB.DE, 1&1,
        SFR, ProtonMail, LaPoste, Outlook Windows) replace or strip <body>,
        losing its CSS. This table is the true layout root.
    -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" bgcolor="{_BG_BODY}" style="background-color: {_BG_BODY}; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
{banner}\
                <!--[if mso]>
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" align="center"><tr><td>
                <![endif]-->
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="width: 100%; max-width: 600px; background-color: {_BG_CARD}; border: 1px solid {_GREEN};" bgcolor="{_BG_CARD}">

                    <!-- Header -->
                    <tr>
                        <td align="center" style="padding: 30px 40px; border-bottom: 1px solid {_GREEN}; font-family: {_FONT}; font-size: 28px; font-weight: bold; color: {_CYAN};">
                            CYBERVPN
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="padding: 8px 40px 0 40px; font-family: {_FONT}; font-size: 14px; color: {_MUTED};">
                            SECURE // PRIVATE // UNTRACEABLE
                        </td>
                    </tr>

                    <!-- Title -->
                    <tr>
                        <td align="center" style="padding: 30px 40px 0 40px; font-family: {_FONT}; font-size: 20px; font-weight: bold; color: {_WHITE};">
                            Verify Your Email Address
                        </td>
                    </tr>

                    <!-- Subtitle -->
                    <tr>
                        <td align="center" style="padding: 12px 40px 30px 40px; font-family: {_FONT}; font-size: 16px; mso-line-height-rule: exactly; line-height: 24px; color: {_TEXT};">
                            Enter the following code to complete your registration:
                        </td>
                    </tr>

                    <!-- OTP Code Box -->
                    <tr>
                        <td align="center" style="padding: 0 40px;">
                            <table role="presentation" width="300" align="center" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td align="center" bgcolor="{_BG_CODE}" style="background-color: {_BG_CODE}; border: 2px solid {_GREEN}; padding: 25px; font-family: {_MONO}; font-size: 36px; font-weight: bold; color: {_CYAN};">
                                        {code}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Expiry -->
                    <tr>
                        <td align="center" style="padding: 20px 40px 0 40px; font-family: {_FONT}; font-size: 14px; color: {_MUTED};">
                            This code expires in <span style="color: {_RED};">{expires_in}</span>
                        </td>
                    </tr>

                    <!-- Disclaimer -->
                    <tr>
                        <td align="center" style="padding: 12px 40px 40px 40px; font-family: {_FONT}; font-size: 13px; color: {_DIM};">
                            If you didn't request this code, you can safely ignore this email.
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding: 20px 40px; border-top: 1px solid {_BORDER}; font-family: {_FONT}; font-size: 12px; color: {_FOOTER};">
                            &copy; 2026 CyberVPN. All rights reserved.
                        </td>
                    </tr>

                </table>
                <!--[if mso]>
                </td></tr></table>
                <![endif]-->
            </td>
        </tr>
    </table>
</body>
</html>"""


def render_magic_link_template(
    magic_link_url: str,
    expires_in: str,
    locale: str,
    otp_code: str = "",
    *,
    dev_banner: bool = False,
) -> str:
    """Render email-compatible magic link email."""
    banner = _dev_banner_html() if dev_banner else ""
    otp_section = _otp_section_html(otp_code) if otp_code else ""
    return f"""\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Sign in to CyberVPN</title>
</head>
<body bgcolor="{_BG_BODY}" style="margin: 0; padding: 0; background-color: {_BG_BODY}; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
    <!-- Outer wrapper duplicates body styles (body may be replaced/stripped) -->
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" bgcolor="{_BG_BODY}" style="background-color: {_BG_BODY}; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
{banner}\
                <!--[if mso]>
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" align="center"><tr><td>
                <![endif]-->
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="width: 100%; max-width: 600px; background-color: {_BG_CARD}; border: 1px solid {_GREEN};" bgcolor="{_BG_CARD}">

                    <!-- Header -->
                    <tr>
                        <td align="center" style="padding: 30px 40px; border-bottom: 1px solid {_GREEN}; font-family: {_FONT}; font-size: 28px; font-weight: bold; color: {_CYAN};">
                            CYBERVPN
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="padding: 8px 40px 0 40px; font-family: {_FONT}; font-size: 14px; color: {_MUTED};">
                            SECURE // PRIVATE // UNTRACEABLE
                        </td>
                    </tr>

                    <!-- Title -->
                    <tr>
                        <td align="center" style="padding: 30px 40px 0 40px; font-family: {_FONT}; font-size: 20px; font-weight: bold; color: {_WHITE};">
                            Sign In to Your Account
                        </td>
                    </tr>

                    <!-- Subtitle -->
                    <tr>
                        <td align="center" style="padding: 12px 40px 30px 40px; font-family: {_FONT}; font-size: 16px; mso-line-height-rule: exactly; line-height: 24px; color: {_TEXT};">
                            Click the button below to securely sign in:
                        </td>
                    </tr>

                    <!-- Bulletproof Button -->
                    <tr>
                        <td align="center" style="padding: 0 40px;">
                            <table role="presentation" align="center" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <!--[if mso]>
                                    <td align="center" bgcolor="{_GREEN}" style="padding: 0;">
                                        <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{magic_link_url}" style="height:52px;v-text-anchor:middle;width:240px;" fillcolor="{_GREEN}" stroke="f">
                                        <w:anchorlock/>
                                        <center style="color:{_BG_BODY};font-family:{_FONT};font-size:18px;font-weight:bold;">SIGN IN</center>
                                        </v:roundrect>
                                    </td>
                                    <![endif]-->
                                    <!--[if !mso]><!-->
                                    <td align="center" bgcolor="{_GREEN}" style="background-color: {_GREEN}; padding: 16px 48px;">
                                        <a href="{magic_link_url}" style="color: {_BG_BODY}; font-size: 18px; font-weight: bold; text-decoration: none; font-family: {_FONT};">
                                            SIGN IN
                                        </a>
                                    </td>
                                    <!--<![endif]-->
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Spacer after button -->
                    <tr>
                        <td style="padding: 15px 0 0 0; font-size: 1px; mso-line-height-rule: exactly; line-height: 1px;">&nbsp;</td>
                    </tr>
{otp_section}\

                    <!-- Expiry -->
                    <tr>
                        <td align="center" style="padding: 8px 40px 0 40px; font-family: {_FONT}; font-size: 14px; color: {_MUTED};">
                            This link expires in <span style="color: {_RED};">{expires_in}</span>
                        </td>
                    </tr>

                    <!-- Fallback URL hint -->
                    <tr>
                        <td align="center" style="padding: 12px 40px 0 40px; font-family: {_FONT}; font-size: 13px; color: {_DIM};">
                            If the button doesn't work, copy and paste this URL:
                        </td>
                    </tr>

                    <!-- Fallback URL -->
                    <tr>
                        <td align="center" style="padding: 6px 40px 0 40px; font-family: {_FONT}; font-size: 12px; color: {_GREEN}; word-wrap: break-word;">
                            {magic_link_url}
                        </td>
                    </tr>

                    <!-- Footer spacer -->
                    <tr>
                        <td style="padding: 20px 0 0 0; font-size: 1px; mso-line-height-rule: exactly; line-height: 1px;">&nbsp;</td>
                    </tr>

                    <!-- Disclaimer -->
                    <tr>
                        <td align="center" style="padding: 20px 40px 8px 40px; border-top: 1px solid {_BORDER}; font-family: {_FONT}; font-size: 12px; color: {_DIM};">
                            If you didn't request this link, you can safely ignore this email.
                        </td>
                    </tr>

                    <!-- Copyright -->
                    <tr>
                        <td align="center" style="padding: 0 40px 20px 40px; font-family: {_FONT}; font-size: 12px; color: {_FOOTER};">
                            &copy; 2026 CyberVPN. All rights reserved.
                        </td>
                    </tr>

                </table>
                <!--[if mso]>
                </td></tr></table>
                <![endif]-->
            </td>
        </tr>
    </table>
</body>
</html>"""


def _otp_section_html(otp_code: str) -> str:
    """Render the inline OTP code section for magic link emails."""
    return f"""
                    <!-- OTP divider text -->
                    <tr>
                        <td align="center" style="padding: 8px 40px; font-family: {_FONT}; font-size: 15px; mso-line-height-rule: exactly; line-height: 22px; color: {_TEXT};">
                            Or enter this code:
                        </td>
                    </tr>

                    <!-- OTP Code Box -->
                    <tr>
                        <td align="center" style="padding: 0 40px;">
                            <table role="presentation" width="300" align="center" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td align="center" bgcolor="{_BG_CODE}" style="background-color: {_BG_CODE}; border: 2px solid {_GREEN}; padding: 25px; font-family: {_MONO}; font-size: 36px; font-weight: bold; color: {_CYAN};">
                                        {otp_code}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Spacer after OTP -->
                    <tr>
                        <td style="padding: 15px 0 0 0; font-size: 1px; mso-line-height-rule: exactly; line-height: 1px;">&nbsp;</td>
                    </tr>
"""


def _dev_banner_html() -> str:
    """Render the DEV MODE banner for SMTP/Mailpit emails."""
    return f"""                <!--[if mso]>
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" align="center"><tr><td>
                <![endif]-->
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="width: 100%; max-width: 600px;">
                    <tr>
                        <td align="center" bgcolor="{_RED}" style="background-color: {_RED}; color: #000000; padding: 10px 20px; font-weight: bold; font-family: {_FONT}; font-size: 14px;">
                            DEV MODE - Sent via Mailpit
                        </td>
                    </tr>
                </table>
                <!--[if mso]>
                </td></tr></table>
                <![endif]-->
                <!-- Banner spacer -->
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                    <tr><td style="padding: 10px 0 0 0; font-size: 1px; mso-line-height-rule: exactly; line-height: 1px;">&nbsp;</td></tr>
                </table>
"""
