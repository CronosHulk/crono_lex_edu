import { describe, expect, it, vi } from "vitest";

import { settingsKey, useMarkPasswordPrompted, useSaveSettings, useSettings, useUpdatePassword } from "./settingsApi";
import { clientApi } from "../../../api/clientApi";

const invalidateQueries = vi.fn();
const useMutationMock = vi.fn((config) => config);
const useQueryMock = vi.fn((config) => config);

vi.mock("@tanstack/react-query", () => ({
  useMutation: (config: unknown) => useMutationMock(config),
  useQuery: (config: unknown) => useQueryMock(config),
  useQueryClient: () => ({ invalidateQueries }),
}));

vi.mock("../../../api/clientApi", () => ({
  clientApi: vi.fn(),
}));

describe("settings api hooks", () => {
  it("builds the settings query", () => {
    const query = useSettings() as unknown as { queryFn: () => unknown; queryKey: readonly string[] };

    expect(query).toMatchObject({ queryKey: settingsKey });
    query.queryFn();
    expect(clientApi).toHaveBeenCalledWith("/settings");
  });

  it("builds the settings mutation and invalidates settings", () => {
    const mutation = useSaveSettings() as unknown as { mutationFn: (payload: unknown) => unknown; onSuccess: () => void };
    const payload = { words_per_session: 20 };

    mutation.mutationFn(payload);
    mutation.onSuccess();

    expect(clientApi).toHaveBeenCalledWith("/settings", { method: "PATCH", body: JSON.stringify(payload) });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: settingsKey });
  });

  it("builds the password update mutation", () => {
    const mutation = useUpdatePassword() as unknown as { mutationFn: (payload: unknown) => unknown; onSuccess: () => void };
    const payload = { password: "Pass1234", confirm_password: "Pass1234" };

    mutation.mutationFn(payload);
    mutation.onSuccess();

    expect(clientApi).toHaveBeenCalledWith("/auth/password", { method: "PATCH", body: JSON.stringify(payload) });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: settingsKey });
  });

  it("builds the password prompt marker mutation", () => {
    const mutation = useMarkPasswordPrompted() as unknown as { mutationFn: () => unknown };

    mutation.mutationFn();

    expect(clientApi).toHaveBeenCalledWith("/auth/password-prompted", { method: "POST", body: "{}" });
  });
});
