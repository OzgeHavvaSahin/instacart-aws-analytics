
import type { OverviewFilters } from "../types/analytics";

export type ProductSort =
  | "units_sold"
  | "estimated_revenue"
  | "reorder_rate";

export interface ProductItem {
  product_id: number;
  product_name: string;
  department_id: number;
  aisle_id: number;
  units_sold: number;
  order_count: number;
  estimated_revenue: number;
  reorder_rate: number;
}

export interface RevenuePoint {
  period: string;
  total_orders: number;
  total_items: number;
  estimated_revenue: number;
}

export interface DepartmentItem {
  department_id: number;
  department_name: string;
  units_sold: number;
  total_orders: number;
  total_customers: number;
  estimated_revenue: number;
  reorder_rate: number;
}

export interface ReorderData {
  total_items: number;
  reordered_items: number;
  first_time_items: number;
  total_orders: number;
  reorder_rate: number;
}

export interface ShoppingPoint {
  day_of_week: number;
  hour_of_day: number;
  total_orders: number;
}

type ApiResponse<T> = {
  success: boolean;
  data?: T;
  error?: {
    message?: string;
  };
};

export function makeQuery(
  filters: OverviewFilters,
  extra: Record<string, string | number> = {}
): string {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries({
    ...filters,
    ...extra,
  })) {
    if (
      value !== null &&
      value !== undefined &&
      value !== ""
    ) {
      params.set(key, String(value));
    }
  }

  return params.toString();
}

// Match this variable to your existing .env.local config.
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/+$/, "");

export async function fetchDashboardData<T>(
  path: string,
  signal?: AbortSignal
): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error(
      "VITE_API_BASE_URL is missing. Configure the Lambda Function URL."
    );
  }

  const response = await fetch(
    `${API_BASE_URL}${path}`,
    { signal }
  );

  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status}: ${response.statusText}`
    );
  }

  const payload =
    (await response.json()) as ApiResponse<T>;

  if (!payload.success || !payload.data) {
    throw new Error(
      payload.error?.message ||
      "Analytics API returned an error"
    );
  }

  return payload.data;
}
