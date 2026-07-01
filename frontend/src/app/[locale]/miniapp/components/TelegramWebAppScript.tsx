import Script from 'next/script';

export function TelegramWebAppScript() {
  return (
    <Script
      id="telegram-web-app"
      src="https://telegram.org/js/telegram-web-app.js"
      strategy="afterInteractive"
    />
  );
}
