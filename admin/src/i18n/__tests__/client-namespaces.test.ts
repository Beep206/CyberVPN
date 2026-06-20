import { describe, expect, it } from 'vitest';
import { DASHBOARD_CLIENT_NAMESPACES } from '../client-namespaces';
import enMessages from '../messages/generated/en-EN.json';
import ruMessages from '../messages/generated/ru-RU.json';

describe('dashboard client namespaces', () => {
  it('ships Support messages to dashboard client routes', () => {
    expect(DASHBOARD_CLIENT_NAMESPACES).toContain('Support');
  });

  it('ships PrivacyRequests messages to dashboard client routes', () => {
    expect(DASHBOARD_CLIENT_NAMESPACES).toContain('PrivacyRequests');
    expect(ruMessages.PrivacyRequests.title).toBe('Запросы приватности');
    expect(enMessages.PrivacyRequests.title).toBe('Privacy requests');
  });
});
