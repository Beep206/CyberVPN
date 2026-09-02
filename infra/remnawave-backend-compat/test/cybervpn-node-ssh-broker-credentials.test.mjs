import assert from 'node:assert/strict';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import test from 'node:test';

const testDir = dirname(fileURLToPath(import.meta.url));
const credentialsModule = resolve(
  testDir,
  '..',
  'overlay',
  'src',
  'modules',
  'node-ssh',
  'cybervpn-node-ssh-broker.credentials.ts',
);

const {
  CYBERVPN_NODE_SSH_TICKET_TTL_SECONDS,
  CYBERVPN_NODE_SSH_WS_PATH,
  CYBERVPN_NODE_SSH_WS_PROTOCOL,
  consumeCybervpnNodeSshTicket,
  compileCybervpnNodeSshTrustedProxyPolicy,
  cybervpnNodeSshBrokerSecretMatches,
  isCybervpnNodeSshUuid,
  issueCybervpnNodeSshTicket,
  normalizeCybervpnNodeSshSourceIp,
  parseCybervpnNodeSshWsCredentials,
  resolveCybervpnNodeSshTrustedSourceIp,
} = await import(pathToFileURL(credentialsModule).href);

const brokerSecret = 'ab'.repeat(64);
const otherBrokerSecret = 'cd'.repeat(64);
const actorReference = '6ba7b810-9dad-41d1-80b4-00c04fd430c8';
const nodeUuid = '7e7d4a35-8f14-45a8-9ad7-7c5a8d858445';

class InMemoryTicketStore {
  entries = new Map();
  lastKey = '';
  lastValue = '';
  lastTtl = 0;

  async set(key, value, ttlSeconds) {
    this.lastKey = key;
    this.lastValue = JSON.stringify(value);
    this.lastTtl = ttlSeconds;
    this.entries.set(key, this.lastValue);
  }

  async getDelString(key) {
    const value = this.entries.get(key) ?? null;
    this.entries.delete(key);
    return value;
  }
}

test('broker secret authentication is exact, fixed-format, and independent of APP_SECRET/JWT', () => {
  assert.equal(cybervpnNodeSshBrokerSecretMatches(brokerSecret, brokerSecret), true);
  assert.equal(cybervpnNodeSshBrokerSecretMatches(brokerSecret, otherBrokerSecret), false);
  assert.equal(cybervpnNodeSshBrokerSecretMatches(brokerSecret, undefined), false);
  assert.equal(cybervpnNodeSshBrokerSecretMatches(brokerSecret, 'short'), false);
  assert.equal(cybervpnNodeSshBrokerSecretMatches(brokerSecret, brokerSecret.toUpperCase()), false);
});

test('ticket and credential are separate opaque values and Redis receives neither raw value', async () => {
  const store = new InMemoryTicketStore();
  const material = await issueCybervpnNodeSshTicket(store, brokerSecret, {
    actorReference,
    clientIp: '192.0.2.10',
    nodeUuid,
  });

  assert.match(material.ticket, /^[A-Za-z0-9_-]{43}$/);
  assert.match(material.credential, /^[A-Za-z0-9_-]{43}$/);
  assert.notEqual(material.ticket, material.credential);
  assert.equal(material.path, CYBERVPN_NODE_SSH_WS_PATH);
  assert.equal(material.protocol, CYBERVPN_NODE_SSH_WS_PROTOCOL);
  assert.equal(material.expiresInSeconds, CYBERVPN_NODE_SSH_TICKET_TTL_SECONDS);
  assert.equal(store.lastTtl, CYBERVPN_NODE_SSH_TICKET_TTL_SECONDS);

  for (const secretValue of [brokerSecret, material.ticket, material.credential]) {
    assert.equal(store.lastKey.includes(secretValue), false);
    assert.equal(store.lastValue.includes(secretValue), false);
  }
});

test('ticket scope stores the normalized source IP used for redemption', async () => {
  const store = new InMemoryTicketStore();
  const material = await issueCybervpnNodeSshTicket(store, brokerSecret, {
    actorReference,
    clientIp: ' 192.0.2.10 ',
    nodeUuid,
  });

  const consumed = await consumeCybervpnNodeSshTicket(
    store,
    brokerSecret,
    { ticket: material.ticket, credential: material.credential },
    '192.0.2.10',
  );
  assert.equal(consumed?.clientIp, '192.0.2.10');
});

test('wrong credential cannot consume the ticket, while the exact pair succeeds only once', async () => {
  const store = new InMemoryTicketStore();
  const material = await issueCybervpnNodeSshTicket(store, brokerSecret, {
    actorReference,
    clientIp: '2001:db8::10',
    nodeUuid,
  });

  const wrongCredential = material.credential.replace(/.$/, (value) =>
    value === 'A' ? 'B' : 'A',
  );
  assert.equal(
    await consumeCybervpnNodeSshTicket(
      store,
      brokerSecret,
      { ticket: material.ticket, credential: wrongCredential },
      '2001:db8::10',
    ),
    null,
  );

  const consumed = await consumeCybervpnNodeSshTicket(
    store,
    brokerSecret,
    { ticket: material.ticket, credential: material.credential },
    '2001:db8::10',
  );
  assert.deepEqual(
    {
      actorReference: consumed?.actorReference,
      clientIp: consumed?.clientIp,
      nodeUuid: consumed?.nodeUuid,
    },
    { actorReference, clientIp: '2001:db8::10', nodeUuid },
  );

  assert.equal(
    await consumeCybervpnNodeSshTicket(
      store,
      brokerSecret,
      { ticket: material.ticket, credential: material.credential },
      '2001:db8::10',
    ),
    null,
  );
});

test('source-IP mismatch fails closed and burns the otherwise valid one-time pair', async () => {
  const store = new InMemoryTicketStore();
  const material = await issueCybervpnNodeSshTicket(store, brokerSecret, {
    actorReference,
    clientIp: '192.0.2.10',
    nodeUuid,
  });

  assert.equal(
    await consumeCybervpnNodeSshTicket(
      store,
      brokerSecret,
      { ticket: material.ticket, credential: material.credential },
      '192.0.2.11',
    ),
    null,
  );
  assert.equal(
    await consumeCybervpnNodeSshTicket(
      store,
      brokerSecret,
      { ticket: material.ticket, credential: material.credential },
      '192.0.2.10',
    ),
    null,
  );
});

test('custom WebSocket protocol parser cannot confuse native rw credentials', () => {
  const ticket = 'A'.repeat(43);
  const credential = 'B'.repeat(43);

  assert.deepEqual(
    parseCybervpnNodeSshWsCredentials(`rw-cybervpn, ${ticket}, ${credential}`),
    { ticket, credential },
  );
  assert.equal(parseCybervpnNodeSshWsCredentials(`rw,${ticket},${credential}`), null);
  assert.equal(parseCybervpnNodeSshWsCredentials(`rw-cybervpn,${ticket}`), null);
  assert.equal(
    parseCybervpnNodeSshWsCredentials(`rw-cybervpn,${ticket},${credential},extra`),
    null,
  );
  assert.equal(parseCybervpnNodeSshWsCredentials('rw-cybervpn,bad,bad'), null);
});

test('source IP normalization rejects missing and non-IP scope', () => {
  assert.equal(normalizeCybervpnNodeSshSourceIp(' 192.0.2.10 '), '192.0.2.10');
  assert.equal(normalizeCybervpnNodeSshSourceIp('2001:db8::10'), '2001:db8::10');
  assert.equal(normalizeCybervpnNodeSshSourceIp(''), null);
  assert.equal(normalizeCybervpnNodeSshSourceIp('backend.internal'), null);
});

test('actor and node references reject unversioned nil UUIDs', async () => {
  assert.equal(isCybervpnNodeSshUuid(actorReference), true);
  assert.equal(isCybervpnNodeSshUuid('00000000-0000-0000-0000-000000000000'), false);

  await assert.rejects(
    issueCybervpnNodeSshTicket(new InMemoryTicketStore(), brokerSecret, {
      actorReference: '00000000-0000-0000-0000-000000000000',
      clientIp: '192.0.2.10',
      nodeUuid,
    }),
    /Invalid CyberVPN Node SSH ticket scope/,
  );
});

test('forwarded source IP is trusted only from an allowlisted socket peer', () => {
  const policy = compileCybervpnNodeSshTrustedProxyPolicy(
    '172.20.0.5,198.51.100.0/24,2001:db8:1::/64',
  );

  assert.equal(
    resolveCybervpnNodeSshTrustedSourceIp(policy, '192.0.2.10', '172.20.0.5'),
    '192.0.2.10',
  );
  assert.equal(
    resolveCybervpnNodeSshTrustedSourceIp(policy, '192.0.2.10', '::ffff:198.51.100.7'),
    '192.0.2.10',
  );
  assert.equal(
    resolveCybervpnNodeSshTrustedSourceIp(policy, '2001:db8:2::10', '2001:db8:1::7'),
    '2001:db8:2::10',
  );

  assert.equal(
    resolveCybervpnNodeSshTrustedSourceIp(policy, '192.0.2.10', '203.0.113.9'),
    null,
  );
  assert.equal(
    resolveCybervpnNodeSshTrustedSourceIp(policy, '192.0.2.10', undefined),
    null,
  );
  assert.equal(
    resolveCybervpnNodeSshTrustedSourceIp(policy, 'spoofed.invalid', '172.20.0.5'),
    null,
  );
});

test('trusted proxy policy rejects broad, malformed, empty, and unbounded configuration', () => {
  for (const value of [
    '',
    '0.0.0.0',
    '0.0.0.1',
    '::',
    '169.254.10.20',
    '224.0.0.1',
    '239.0.0.0/24',
    'ff02::1',
    '0.0.0.0/0',
    '0.0.0.0/1',
    '10.0.0.0/8',
    '::/0',
    '::/1',
    '2001:db8::/32',
    '172.20.0.5,',
    'not-an-ip',
    '172.20.0.0/not-a-prefix',
    '172.20.0.0/33',
    '2001:db8::/129',
    Array.from({ length: 33 }, (_, index) => `192.0.2.${index + 1}`).join(','),
  ]) {
    assert.throws(
      () => compileCybervpnNodeSshTrustedProxyPolicy(value),
      /trusted proxy range/,
      value,
    );
  }
});

test('trusted proxy policy permits exact peers and only narrow IPv4/IPv6 networks', () => {
  const policy = compileCybervpnNodeSshTrustedProxyPolicy(
    '127.0.0.1,192.0.2.9/32,198.51.100.0/24,::1,2001:db8:1::7/128,2001:db8:2::/64',
  );

  for (const peer of [
    '127.0.0.1',
    '192.0.2.9',
    '198.51.100.200',
    '::1',
    '2001:db8:1::7',
    '2001:db8:2::ff',
  ]) {
    assert.equal(policy.allows(peer), true, peer);
  }
  assert.equal(policy.allows('198.51.101.1'), false);
  assert.equal(policy.allows('2001:db8:3::1'), false);
});
