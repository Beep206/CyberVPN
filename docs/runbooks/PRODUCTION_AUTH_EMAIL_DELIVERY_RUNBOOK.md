# Production Auth Email Delivery Runbook

This runbook covers CyberVPN auth/system email delivery through the
`cyber-vpn.net` mail server. It intentionally contains no mailbox passwords,
API tokens, OTP codes, or customer email contents.

## Runtime Contract

`services/task-worker` sends auth/system mail through SMTP primary outside
`EMAIL_DEV_MODE`. Resend is allowed only for explicit resend/fallback tasks
when `EMAIL_RESEND_FALLBACK_ENABLED=true` and a valid `RESEND_API_KEY` exists.

Production app hosts must provide these runtime env variables from secret
storage:

```dotenv
SMTP_HOST=mail.cyber-vpn.net
SMTP_PORT=2587
SMTP_STARTTLS=true
SMTP_USE_SSL=false
SMTP_AUTH_USERNAME=noreply@cyber-vpn.net
SMTP_AUTH_PASSWORD=<runtime-secret>
SMTP_SYSTEM_FROM_EMAIL=CyberVPN <noreply@cyber-vpn.net>
SMTP_BILLING_FROM_EMAIL=CyberVPN Billing <billing@cyber-vpn.net>
SMTP_SUPPORT_FROM_EMAIL=CyberVPN Support <support@cyber-vpn.net>
EMAIL_VERIFIED_SENDER_DOMAINS=cyber-vpn.net,email.cyber-vpn.net
EMAIL_RESEND_FALLBACK_ENABLED=true
EMAIL_DEV_MODE=false
```

Use `SMTP_PORT=587` only when the app host can reach standard SMTP submission
ports. The current rented production app host blocks or cannot route standard
SMTP ports to `mail.cyber-vpn.net`, so production uses the alternative
submission port `2587`.

## Mail Server Alternative Submission Port

The mail server runs Stalwart on standard submission port `587`. To support app
hosts with restricted SMTP egress, the mail server also exposes `2587` and
proxies it locally to Stalwart `127.0.0.1:587` by systemd socket activation.

Install or repair the socket-proxy on the mail server:

```bash
install -o root -g root -m 0644 infra/mail/stalwart-submission-alt.socket \
  /etc/systemd/system/stalwart-submission-alt.socket
install -o root -g root -m 0644 infra/mail/stalwart-submission-alt.service \
  /etc/systemd/system/stalwart-submission-alt.service
systemctl daemon-reload
systemctl enable --now stalwart-submission-alt.socket
ufw allow 2587/tcp comment "CyberVPN app SMTP submission alt"
```

Expected mail-server checks:

```bash
systemctl is-active stalwart-submission-alt.socket
systemctl is-enabled stalwart-submission-alt.socket
ss -ltnp | grep 2587
ufw status numbered | grep 2587
```

## App Host Apply

Update the production app secret env file, preserving file ownership and mode:

```bash
cd /srv/cybervpn/compose/app
sudo cp -a /srv/cybervpn/secrets/app.env \
  /srv/cybervpn/secrets/app.env.pre-smtp-prod-fix-$(date -u +%Y%m%dT%H%M%SZ)
sudoedit /srv/cybervpn/secrets/app.env
sudo docker compose up -d --force-recreate cybervpn-worker cybervpn-scheduler
```

Do not print or commit `SMTP_AUTH_PASSWORD`, `RESEND_API_KEY`, or mailbox
passwords.

## Verification

From the production app host:

```bash
nc -4 -vz -w 10 mail.cyber-vpn.net 2587
cd /srv/cybervpn/compose/app
sudo docker compose ps cybervpn-worker cybervpn-scheduler
```

From inside `cybervpn-worker`, verify SMTP STARTTLS login using only container
env values:

```bash
cd /srv/cybervpn/compose/app
sudo docker compose exec -T cybervpn-worker python - <<'PY'
import os
import smtplib

host = os.environ["SMTP_HOST"]
port = int(os.environ["SMTP_PORT"])
user = os.environ["SMTP_AUTH_USERNAME"]
password = os.environ["SMTP_AUTH_PASSWORD"]

with smtplib.SMTP(host, port, timeout=15) as smtp:
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login(user, password)
    smtp.noop()

print("smtp_login=ok")
PY
```

Check for recent startup/config/delivery failures:

```bash
cd /srv/cybervpn/compose/app
sudo docker compose logs --since=5m cybervpn-worker cybervpn-scheduler 2>&1 \
  | grep -iE "smtp_send_failed|otp_email_failed|ValidationError|SMTP_AUTH|EMAIL_VERIFIED" || true
```

## Rollback

If standard port `587` is reachable again from the app host, set
`SMTP_PORT=587` in `/srv/cybervpn/secrets/app.env` and recreate worker services.

To remove the alternative submission port from the mail server:

```bash
systemctl disable --now stalwart-submission-alt.socket
rm -f /etc/systemd/system/stalwart-submission-alt.socket
rm -f /etc/systemd/system/stalwart-submission-alt.service
systemctl daemon-reload
ufw delete allow 2587/tcp
```

## 2026-06-19 Incident Notes

- `cybervpn-worker` initially failed closed after CYBA-717 because production
  secret env missed required `SMTP_AUTH_USERNAME`/`SMTP_AUTH_PASSWORD`.
- After SMTP env was added, queued OTP delivery selected provider `smtp` and
  failed while connecting to `mail.cyber-vpn.net:587`.
- The app host could reach the mail server on SSH/HTTP/HTTPS, but not SMTP
  submission ports. Packet capture on the mail server showed the failed SMTP
  SYN did not arrive.
- `mail.cyber-vpn.net:2587` via the systemd socket-proxy restored app-host SMTP
  connectivity, and `cybervpn-worker` SMTP STARTTLS login succeeded.
