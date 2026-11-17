
import { useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

import type {
  OverviewFilters,
  ProductItem,
  ProductSort,
} from "../types/analytics";

import { makeQuery } from "../api/analytics";

import { useAnalytics } from "../hooks/useAnalytics";

type Props = {
  filters: OverviewFilters;
};

const formatNumber = new Intl.NumberFormat("en-US");

const formatCurrency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const labels: Record<ProductSort, string> = {
  units_sold: "Units Sold",
  estimated_revenue: "Revenue",
  reorder_rate: "Reorder Rate",
};

export default function TopProductsChart({
  filters,
}: Props) {
  const [limit, setLimit] = useState(10);
  const [metric, setMetric] =
    useState<ProductSort>("units_sold");

  const query = makeQuery(filters, {
    limit,
    sort_by: metric,
    sort_order: "desc",
  });

  const { data, loading, error } = useAnalytics<{
    items: ProductItem[];
  }>(`/api/analytics/products?${query}`);

  const products = data?.items ?? [];

  function formatValue(value: number) {
    if (metric === "estimated_revenue") {
      return formatCurrency.format(value);
    }

    if (metric === "reorder_rate") {
      return `${value.toFixed(2)}%`;
    }

    return formatNumber.format(value);
  }

  return (
    <section className="panel analytics-panel">
      <div className="panel-heading">
        <div>
          <h2>Top Products</h2>
          <p>Product ranking and performance</p>
        </div>
      </div>

      <div className="analytics-controls">
        <label>
          Show
          <select
            value={limit}
            onChange={(event) =>
              setLimit(Number(event.target.value))
            }
          >
            <option value={5}>Top 5</option>
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
          </select>
        </label>

        <label>
          Rank by
          <select
            value={metric}
            onChange={(event) =>
              setMetric(
                event.target.value as ProductSort
              )
            }
          >
            <option value="units_sold">
              Units Sold
            </option>
            <option value="estimated_revenue">
              Revenue
            </option>
            <option value="reorder_rate">
              Reorder Rate
            </option>
          </select>
        </label>
      </div>

      {loading && (
        <p className="empty-message">
          Loading products...
        </p>
      )}

      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && products.length === 0 && (
        <p className="empty-message">
          No products found.
        </p>
      )}

      {!loading && !error && products.length > 0 && (
        <div
          className="analytics-chart"
          style={{
            height: Math.max(
              320,
              products.length * 44
            ),
          }}
        >
          <ResponsiveContainer
            width="100%"
            height="100%"
          >
            <BarChart
              data={products}
              layout="vertical"
              margin={{
                top: 8,
                right: 24,
                bottom: 8,
                left: 8,
              }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                horizontal={false}
              />

              <XAxis
                type="number"
                tick={{ fontSize: 11 }}
              />

              <YAxis
                type="category"
                dataKey="product_name"
                width={140}
                tick={{ fontSize: 11 }}
                tickFormatter={(name: string) =>
                  name.length > 22
                    ? `${name.slice(0, 19)}...`
                    : name
                }
              />

              <Tooltip
                formatter={(value) => [
                  formatValue(Number(value)),
                  labels[metric],
                ]}
              />

              <Bar
                dataKey={metric}
                name={labels[metric]}
                fill="#169b7a"
                radius={[0, 5, 5, 0]}
                maxBarSize={25}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
