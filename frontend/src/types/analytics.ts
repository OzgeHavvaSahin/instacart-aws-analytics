export interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface HealthData {
  service: string;
  status: string;
  version: string;
}

export interface SummaryData {
  total_orders: number;
  total_customers: number;
  total_items: number;
  estimated_revenue: number;
  currency: string;
  revenue_type: "synthetic";
}
