import { describe, expect, it } from 'vitest';
import { getOfficialSupportProfile } from '../official-support-routing';

describe('official support routing profile', () => {
  it('uses S1-approved support contacts and response window', () => {
    const profile = getOfficialSupportProfile();

    expect(profile.supportEmail).toBe('support@cyber-vpn.net');
    expect(profile.refundEmail).toBe('refund@cyber-vpn.net');
    expect(profile.communicationSenderEmail).toBe('support@cyber-vpn.net');
    expect(profile.responseWindow).toBe('<=12h beta first response');
  });

  it('keeps web ticket and Telegram support entrypoints explicit', () => {
    const profile = getOfficialSupportProfile();

    expect(profile.webTicketPath).toBe('/contact');
    expect(profile.helpCenterPath).toBe('/help');
    expect(profile.telegramBotUrl).toBe('https://t.me/cybervpn_bot');
  });
});
