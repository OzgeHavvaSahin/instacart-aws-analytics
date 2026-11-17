
import { useEffect, useState } from "react";

import {
  fetchAnalyticsData,
} from "../api/analytics";

type CacheEntry = {
  value: unknown;
  expiresAt: number;
};

const CACHE_TTL_MS = 5 * 60 * 1000;

const cache = new Map<string, CacheEntry>();

const pendingRequests = new Map<
  string,
  Promise<unknown>
>();

async function loadCached<T>(
  path: string
): Promise<T> {
  const cached = cache.get(path);

  if (cached) {
    if (cached.expiresAt > Date.now()) {
      return cached.value as T;
    }

    cache.delete(path);
  }

  const pending = pendingRequests.get(path);

  if (pending) {
    return pending as Promise<T>;
  }

  const request = fetchAnalyticsData<T>(path)
    .then((value) => {
      cache.set(path, {
        value,
        expiresAt: Date.now() + CACHE_TTL_MS,
      });

      return value;
    })
    .finally(() => {
      pendingRequests.delete(path);
    });

  pendingRequests.set(path, request);

  return request;
}

export function useAnalytics<T>(path: string) {
  const [state, setState] = useState<{
    path: string;
    data: T | null;
    loading: boolean;
    error: string | null;
  }>({
    path,
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let active = true;

    loadCached<T>(path)
      .then((data) => {
        if (!active) return;

        setState({
          path,
          data,
          loading: false,
          error: null,
        });
      })
      .catch((error: unknown) => {
        if (!active) return;

        setState({
          path,
          data: null,
          loading: false,
          error:
            error instanceof Error
              ? error.message
              : "Analytics request failed",
        });
      });

    return () => {
      active = false;
    };
  }, [path]);

  if (state.path !== path) {
    return {
      data: null,
      loading: true,
      error: null,
    };
  }

  return {
    data: state.data,
    loading: state.loading,
    error: state.error,
  };
}
