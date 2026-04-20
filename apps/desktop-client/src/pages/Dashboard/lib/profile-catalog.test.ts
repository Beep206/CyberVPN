import { describe, expect, it } from "vitest";

import type { ProfileGroup, ProxyNode, Subscription } from "../../../shared/api/ipc";
import {
  buildDashboardProfileCollections,
  buildDashboardRegionClusters,
  explainDashboardSmartRoute,
  findBestLatencyProxy,
  findBestSmartRoute,
  inferDashboardRegionFlag,
  inferDashboardRegionLabel,
  rankDashboardSmartProxies,
  resolveDashboardSelection,
  sortPinnedFavoriteProxies,
  sortDashboardVisibleProxies,
} from "./profile-catalog";

function createProxyNode(overrides: Partial<ProxyNode>): ProxyNode {
  return {
    id: overrides.id ?? crypto.randomUUID(),
    name: overrides.name ?? "Node",
    server: overrides.server ?? "1.1.1.1",
    port: overrides.port ?? 443,
    protocol: overrides.protocol ?? "vless",
    ...overrides,
  };
}

describe("buildDashboardProfileCollections", () => {
  it("groups proxies by group first, then subscription, then manual bucket", () => {
    const subscriptions: Subscription[] = [
      { id: "sub-1", name: "Europe Fleet", url: "https://example.com/sub", autoUpdate: true },
    ];
    const groups: ProfileGroup[] = [{ id: "grp-1", name: "Streaming" }];
    const profiles: ProxyNode[] = [
      createProxyNode({ id: "a", name: "Berlin", subscriptionId: "sub-1" }),
      createProxyNode({ id: "b", name: "Frankfurt", groupId: "grp-1", subscriptionId: "sub-1" }),
      createProxyNode({ id: "c", name: "Manual Alpha", protocol: "trojan" }),
    ];

    const collections = buildDashboardProfileCollections(profiles, subscriptions, groups);

    expect(collections).toHaveLength(3);
    expect(collections.map((collection) => collection.key)).toEqual([
      "group:grp-1",
      "subscription:sub-1",
      "manual",
    ]);
    expect(collections[0]).toMatchObject({
      label: "Streaming",
      source: "group",
      proxyCount: 1,
    });
    expect(collections[1]).toMatchObject({
      label: "Europe Fleet",
      source: "subscription",
      proxyCount: 1,
    });
    expect(collections[2]).toMatchObject({
      label: "Manual Profiles",
      source: "manual",
      proxyCount: 1,
      protocols: ["TROJAN"],
    });
  });

  it("sorts collection proxies by measured latency before name", () => {
    const profiles: ProxyNode[] = [
      createProxyNode({ id: "slow", name: "Slow", ping: 120, subscriptionId: "sub-1" }),
      createProxyNode({ id: "fast", name: "Fast", ping: 18, subscriptionId: "sub-1" }),
      createProxyNode({ id: "timeout", name: "Timeout", ping: 0, subscriptionId: "sub-1" }),
      createProxyNode({ id: "unknown", name: "Unknown", subscriptionId: "sub-1" }),
    ];

    const collections = buildDashboardProfileCollections(
      profiles,
      [{ id: "sub-1", name: "Europe Fleet", url: "https://example.com/sub", autoUpdate: true }],
      []
    );

    expect(collections[0]?.proxies.map((proxy) => proxy.id)).toEqual([
      "fast",
      "slow",
      "timeout",
      "unknown",
    ]);
  });
});

describe("favorite and latency helpers", () => {
  const proxies: ProxyNode[] = [
    createProxyNode({ id: "favorite", name: "Favorite", ping: 145 }),
    createProxyNode({ id: "fast", name: "Fast", ping: 18 }),
    createProxyNode({ id: "timeout", name: "Timeout", ping: 0 }),
    createProxyNode({ id: "unknown", name: "Unknown" }),
  ];

  it("pins favorite proxies above pure latency sorting", () => {
    expect(sortDashboardVisibleProxies(proxies, new Set(["favorite"])).map((proxy) => proxy.id)).toEqual([
      "favorite",
      "fast",
      "timeout",
      "unknown",
    ]);
  });

  it("preserves the explicit launchpad order for favorites", () => {
    expect(
      sortPinnedFavoriteProxies(proxies, ["timeout", "favorite", "fast"]).map((proxy) => proxy.id)
    ).toEqual(["timeout", "favorite", "fast", "unknown"]);
  });

  it("finds the best measured latency and ignores timeout placeholders", () => {
    expect(findBestLatencyProxy(proxies)?.id).toBe("fast");
  });

  it("uses smart route scoring to prefer trusted stable routes without ignoring latency completely", () => {
    const ranked = rankDashboardSmartProxies(proxies, {
      favoriteProfileIds: new Set(["favorite"]),
      lastStableProfileId: "favorite",
    });

    expect(ranked[0]?.proxy.id).toBe("favorite");
    expect(findBestSmartRoute(proxies, {
      favoriteProfileIds: new Set(["favorite"]),
      lastStableProfileId: "favorite",
    })?.id).toBe("favorite");
    expect(findBestSmartRoute(proxies, {
      favoriteProfileIds: new Set(["favorite"]),
      lastStableProfileId: "timeout",
    })?.id).toBe("fast");
  });

  it("describes smart route signals and summary reasons for operator UI", () => {
    const explanation = explainDashboardSmartRoute(
      createProxyNode({
        id: "live-favorite",
        name: "Frankfurt Relay",
        server: "de1.example.com",
        ping: 82,
        nextHopId: "relay-a",
      }),
      {
        favoriteProfileIds: new Set(["live-favorite"]),
        lastStableProfileId: "live-favorite",
        activeProfileId: "live-favorite",
      }
    );

    expect(explanation.summaryKey).toBe("dashboard.smartRouteReasonTrusted");
    expect(explanation.regionLabel).toBe("Germany");
    expect(explanation.signals.filter((signal) => signal.active)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ kind: "latency", weight: 238 }),
        expect.objectContaining({ kind: "favorite", weight: 60 }),
        expect.objectContaining({ kind: "stable", weight: 90 }),
        expect.objectContaining({ kind: "active", weight: 24 }),
        expect.objectContaining({ kind: "relay", weight: -16 }),
      ])
    );
  });

  it("marks routes without measured latency as fallback candidates", () => {
    const explanation = explainDashboardSmartRoute(
      createProxyNode({
        id: "cold-route",
        name: "Cold Route",
        server: "203.0.113.15",
      })
    );

    expect(explanation.summaryKey).toBe("dashboard.smartRouteReasonFallback");
    expect(explanation.signals).toContainEqual(
      expect.objectContaining({ kind: "fallback", active: true, weight: -140 })
    );
  });
});

describe("region clustering helpers", () => {
  it("infers readable regions from server and name heuristics", () => {
    expect(inferDashboardRegionLabel(createProxyNode({
      name: "Any route",
      server: "de1.gofizzin.com",
    }))).toBe("Germany");

    expect(inferDashboardRegionLabel(createProxyNode({
      name: "Frankfurt Edge",
      server: "203.0.113.10",
    }))).toBe("Frankfurt");
  });

  it("resolves real flag glyphs for country and city heuristics", () => {
    expect(inferDashboardRegionFlag(createProxyNode({
      name: "Any route",
      server: "se1.example.com",
    }))).toBe("🇸🇪");

    expect(inferDashboardRegionFlag(createProxyNode({
      name: "Frankfurt Edge",
      server: "203.0.113.10",
    }))).toBe("🇩🇪");

    expect(inferDashboardRegionFlag(createProxyNode({
      name: "Unmapped Edge",
      server: "203.0.113.11",
    }))).toBe("🌐");
  });

  it("aggregates clusters by region with latency and favorite counts", () => {
    const clusters = buildDashboardRegionClusters(
      [
        createProxyNode({ id: "de-a", name: "Berlin Core", server: "de1.example.com", ping: 42 }),
        createProxyNode({ id: "de-b", name: "Frankfurt Core", server: "de2.example.com", ping: 58 }),
        createProxyNode({ id: "sg-a", name: "Singapore Edge", server: "sg3.example.com", ping: 118 }),
      ],
      new Set(["de-b"])
    );

    expect(clusters[0]).toMatchObject({
      label: "Germany",
      proxyCount: 2,
      favoriteCount: 1,
      bestLatency: 42,
      dominantProtocol: "VLESS",
    });
    expect(clusters[1]).toMatchObject({
      label: "Singapore",
      proxyCount: 1,
      favoriteCount: 0,
      bestLatency: 118,
    });
  });
});

describe("resolveDashboardSelection", () => {
  const collections = buildDashboardProfileCollections(
    [
      createProxyNode({ id: "node-a", name: "A", subscriptionId: "sub-1" }),
      createProxyNode({ id: "node-b", name: "B", subscriptionId: "sub-1" }),
      createProxyNode({ id: "node-c", name: "C" }),
    ],
    [{ id: "sub-1", name: "Europe Fleet", url: "https://example.com/sub", autoUpdate: true }],
    []
  );

  it("prefers an explicitly selected proxy when it is still available", () => {
    expect(
      resolveDashboardSelection(collections, {
        selectedCollectionKey: "manual",
        selectedProxyId: "node-b",
        persistedProxyId: "node-c",
      })
    ).toEqual({
      collectionKey: "subscription:sub-1",
      proxyId: "node-b",
    });
  });

  it("falls back to the persisted proxy and then to the first proxy in the chosen collection", () => {
    expect(
      resolveDashboardSelection(collections, {
        selectedCollectionKey: "manual",
        selectedProxyId: "missing",
        persistedProxyId: "node-c",
      })
    ).toEqual({
      collectionKey: "manual",
      proxyId: "node-c",
    });

    expect(
      resolveDashboardSelection(collections, {
        selectedCollectionKey: "subscription:sub-1",
        selectedProxyId: null,
        persistedProxyId: "missing",
      })
    ).toEqual({
      collectionKey: "subscription:sub-1",
      proxyId: "node-a",
    });
  });
});
