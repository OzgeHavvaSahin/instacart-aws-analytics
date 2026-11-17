import { useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

import type {
  OverviewFilters,
  RevenuePoint,
} from "../types/analytics";

import { makeQuery } from "../api/analytics";

import { useAnalytics } from "../hooks/useAnalytics";

type Props = {
  filters: OverviewFilters;
};

type Granularity = "day" | "week" | "month";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

export default function RevenueTrendChart({
  filters,
}: Props) {
  const [granularity, setGranularity] =
    useState<Granularity>("month");

  const query = makeQuery(filters, {
    granularity,
  });

  const { data, loading, error } = useAnalytics<{
    trends: RevenuePoint[];
  }>(`/api/analytics/revenue-trend?${query}`);

  const trends = (data?.trends ?? []).map(
    (item) => ({
      ...item,
      label: item.period.slice(0, 10),
    })
  );

  return (
    <section className="panel analytics-panel">
      <div className="panel-heading">
        <div>
          <h2>Revenue Trend</h2>
          <p>Estimated revenue over time</p>
        </div>
      </div>

      <div className="analytics-controls">
        <label>
          Group by
          <select
            value={granularity}
            onChange={(event) =>
              setGranularity(
                event.target.value as Granularity
              )
            }
          >
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
            <option value="month">Monthly</option>
          </select>
        </label>
      </div>

      {loading && (
        <p className="empty-message">
          Loading revenue trend...
        </p>
      )}

      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && trends.length === 0 && (
        <p className="empty-message">
          No revenue data found.
        </p>
      )}

      {!loading && !error && trends.length > 0 && (
        <div className="analytics-chart">
          <ResponsiveContainer
            width="100%"
            height="100%"
          >
            <AreaChart
              data={trends}
              margin={{
                top: 14,
                right: 20,
                left: 8,
                bottom: 10,
              }}
            >
              <defs>
                <linearGradient
                  id="revenueGradient"
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop
                    offset="0%"
                    stopColor="#169b7a"
                    stopOpacity={0.3}
                  />
                  <stop
                    offset="100%"
                    stopColor="#169b7a"
                    stopOpacity={0.02}
                  />
                </linearGradient>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
              />

              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                minTickGap={30}
              />

              <YAxis
                width={65}
                tick={{ fontSize: 11 }}
                tickFormatter={(value: number) =>
                  value >= 1000
                    ? `${(value / 1000).toFixed(0)}k`
                    : String(value)
                }
              />

              <Tooltip
                formatter={(value) => [
                  currency.format(Number(value)),
                  "Revenue",
                ]}
              />

              <Area
                type="monotone"
                dataKey="estimated_revenue"
                name="Revenue"
                stroke="#169b7a"
                strokeWidth={3}
                fill="url(#revenueGradient)"
                dot={false}
                activeDot={{ r: 5 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
