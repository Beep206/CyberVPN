import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { JsonLd } from '@/shared/lib/json-ld';

describe('JsonLd', () => {
  it('sanitizes angle brackets in the serialized payload', () => {
    const { container } = render(
      <JsonLd
        data={{
          '@context': 'https://schema.org',
          '@type': 'Thing',
          name: '<unsafe>',
        }}
      />,
    );

    const script = container.querySelector('script');

    expect(script).not.toBeNull();
    expect(script?.innerHTML).toContain('\\u003cunsafe>');
    expect(script?.innerHTML).not.toContain('<unsafe>');
  });
});
