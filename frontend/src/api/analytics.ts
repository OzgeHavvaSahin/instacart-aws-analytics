import { apiGet } from "./client";

import type {
  ApiResponse,
  FiltersData,
  OverviewData,
  OverviewFilters,
} from "../types/analytics";

const filtersCache = new Map<
  string,
  Promise<ApiResponse<FiltersData>>
>();

export function fetchFilters(departmentId?: number) {
  const key =
    departmentId === undefined
      ? "all"
      : String(departmentId);

  const cached = filtersCache.get(key);

  if (cached) {
    return cached;
  }

  const params = new URLSearchParams();

  if (departmentId !== undefined) {
    params.set("department_id", String(departmentId));
  }

  const query = params.toString();

  const request = apiGet<ApiResponse<FiltersData>>(
    `/api/filters${query ? `?${query}` : ""}`
  )
    .then((response) => {
      if (!response.success) {
        throw new Error("Filter API returned an error");
      }

      return response;
    })
    .catch((error: unknown) => {
      filtersCache.delete(key);
      throw error;
    });

  filtersCache.set(key, request);

  return request;
}

export function clearFiltersCache() {
  filtersCache.clear();
}

export function fetchOverview(filters: OverviewFilters) {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(filters)) {
    if (
      value !== undefined &&
      value !== null &&
      value !== ""
    ) {
      params.set(key, String(value));
    }
  }

  const query = params.toString();

  return apiGet<ApiResponse<OverviewData>>(
    `/api/analytics/overview${query ? `?${query}` : ""}`
  );
}


export function fetchOrdersTrend() {
  return apiGet<unknown>("/api/orders-trend");
}
