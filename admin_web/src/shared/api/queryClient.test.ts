import { describe, expect, it } from "vitest";

import { ADMIN_QUERY_DEFAULTS, createAdminQueryClient } from "./queryClient";

describe("createAdminQueryClient", () => {
  it("uses admin query defaults for server state", () => {
    const client = createAdminQueryClient();
    const defaults = client.getDefaultOptions();

    expect(defaults.queries).toMatchObject(ADMIN_QUERY_DEFAULTS);
    expect(defaults.mutations).toMatchObject({ retry: false });
  });
});
