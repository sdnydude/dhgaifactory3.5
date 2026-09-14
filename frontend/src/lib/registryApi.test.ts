import { afterEach, describe, expect, it, vi } from "vitest";

import { getMyReviews } from "./registryApi";

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetch(body: unknown) {
  const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(
    async () =>
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("getMyReviews", () => {
  it("sends reviewer_email and status_filter through the registry proxy", async () => {
    const fetchMock = stubFetch({ reviews: [], count: 0 });

    await getMyReviews("reviewer@example.com", "active");

    const url = fetchMock.mock.calls[0][0];
    expect(url).toBe(
      "/api/registry/api/cme/my-reviews?reviewer_email=reviewer%40example.com&status_filter=active",
    );
  });
});
