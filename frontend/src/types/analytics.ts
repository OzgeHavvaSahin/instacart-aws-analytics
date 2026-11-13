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


export interface FilterOption {
  id: number;
  name: string;
}

export interface FiltersData {
  departments: FilterOption[];
  aisles: FilterOption[];
  date_range: {
    min: string | null;
    max: string | null;
  };
  selected_department_id: number | null;
  date_type: "synthetic";
}

export interface OverviewFilters {
  date_from?: string;
  date_to?: string;
  department_id?: number;
  aisle_id?: number;
  reordered?: boolean;
}

export interface OverviewData {
  total_orders: number;
  total_customers: number;
  total_items: number;
  estimated_revenue: number;
  avg_basket_size: number;
  reorder_rate: number;
  currency: string;
  revenue_type: "synthetic";
  date_type: "synthetic";
  applied_filters: {
    date_from: string | null;
    date_to: string | null;
    department_id: number | null;
    aisle_id: number | null;
    reordered: boolean | null;
  };
}
