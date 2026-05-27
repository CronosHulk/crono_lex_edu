import { describe, expect, it } from "vitest";

import { CLIENT_QUERY_DEFAULTS, clientQueryClient, createClientQueryClient } from "./queryClient";

describe("queryClient", () => {
  it("uses the shared query defaults", () => {
    const client = createClientQueryClient();

    expect(CLIENT_QUERY_DEFAULTS).toMatchObject({
      staleTime: 30_000,
      gcTime: 300_000,
      retry: 1,
      refetchOnWindowFocus: false,
    });
    expect(client.getDefaultOptions().queries).toMatchObject(CLIENT_QUERY_DEFAULTS);
    expect(client.getDefaultOptions().mutations).toMatchObject({ retry: false });
    expect(clientQueryClient.getDefaultOptions().queries).toMatchObject(CLIENT_QUERY_DEFAULTS);
  });
});
