import { describe, expect, it } from 'vitest';
import { MARKETING_CLIENT_NAMESPACES } from '../client-namespaces';

describe('client namespace scopes', () => {
  it('loads public header notification namespaces on marketing routes', () => {
    expect(MARKETING_CLIENT_NAMESPACES).toEqual(
      expect.arrayContaining(['Header', 'Messaging']),
    );
  });
});
