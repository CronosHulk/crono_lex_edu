import { QueryClient } from "@tanstack/react-query";

export const CLIENT_QUERY_DEFAULTS = {
  staleTime: 30_000,
  gcTime: 5 * 60_000,
  retry: 1,
  refetchOnWindowFocus: false,
} as const;

export function createClientQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: CLIENT_QUERY_DEFAULTS,
      mutations: {
        retry: false,
      },
    },
  });
}

export const clientQueryClient = createClientQueryClient();
