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
  DepartmentItem,
} from "../types/analytics";

import { makeQuery } from "../api/analytics";

import { useAnalytics } from "../hooks/useAnalytics";


type Props = {
  filters: OverviewFilters;
};

type Metric = "estimated_revenue" | "units_sold";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const number = new Intl.NumberFormat("en-US");

export default function DepartmentPerformanceChart({
  filters,
}: Props) {
  const [metric, setMetric] =
    useState<Metric>("estimated_revenue");

  const query = makeQuery(filters);

  const { data, loading, error } = useAnalytics<{
    items: DepartmentItem[];
  }>(`/api/analytics/departments?${query}`);

  const departments = [
    ...(data?.items ?? []),
  ].sort((a, b) => b[metric] - a[metric]);

  return (
    <section className="panel analytics-panel">
      <div className="panel-heading">
        <div>
          <h2>Department Performance</h2>
          <p>Compare department-level results</p>
        </div>
      </div>

      <div className="analytics-controls">
        <label>
          Metric
          <select
            value={metric}
            onChange={(event) =>
              setMetric(event.target.value as Metric)
            }
          >
            <option value="estimated_revenue">
              Revenue
            </option>
            <option value="units_sold">
              Units Sold
            </option>
          </select>
        </label>
      </div>

      {loading && (
        <p className="empty-message">
          Loading departments...
        </p>
      )}

      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && departments.length === 0 && (
        <p className="empty-message">
          No department data found.
        </p>
      )}

      {!loading && !error && departments.length > 0 && (
        <div
          className="analytics-chart"
          style={{
            height: Math.max(
              330,
              departments.length * 38
            ),
          }}
        >
          <ResponsiveContainer
            width="100%"
            height="100%"
          >
            <BarChart
              data={departments}
              layout="vertical"
              margin={{
                top: 10,
                right: 25,
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
                dataKey="department_name"
                width={135}
                tick={{ fontSize: 11 }}
              />

              <Tooltip
                formatter={(value) => [
                  metric === "estimated_revenue"
                    ? currency.format(Number(value))
                    : number.format(Number(value)),
                  metric === "estimated_revenue"
                    ? "Revenue"
                    : "Units Sold",
                ]}
              />

              <Bar
                dataKey={metric}
                name={
                  metric === "estimated_revenue"
                    ? "Revenue"
                    : "Units Sold"
                }
                fill="#3f72a8"
                radius={[0, 5, 5, 0]}
                maxBarSize={24}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
