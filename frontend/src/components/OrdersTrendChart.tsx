
import { useEffect, useState } from "react";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

import { fetchOrdersTrend } from "../api/analytics";

type TrendPoint = {
  date: string;
  orders: number;
  customers: number;
};

function isRecord(
  value: unknown
): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}


function extractRows(value: unknown): unknown[] {
  if (Array.isArray(value)) {
    return value;
  }

  if (!isRecord(value)) {
    return [];
  }

  for (const key of [
    "trends",
    "data",
    "results",
    "items",
    "trend",
    "series",
    "rows",
  ]) {
    const nested = extractRows(value[key]);

    if (nested.length > 0) {
      return nested;
    }
  }

  return [];
}



function normalizeTrend(value: unknown): TrendPoint[] {
  return extractRows(value)
    .flatMap((entry): TrendPoint[] => {
      if (!isRecord(entry)) return [];

      const date = entry.date;
      const orders = Number(entry.total_orders);
      const customers = Number(entry.total_customers);

      if (
        typeof date !== "string" ||
        !Number.isFinite(orders) ||
        !Number.isFinite(customers)
      ) {
        return [];
      }

      return [{
        date,
        orders,
        customers,
      }];
    })
    .sort((a, b) => a.date.localeCompare(b.date));
}


export default function OrdersTrendChart() {
  const [data, setData] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(
    null
  );

  const [raw, setRaw] = useState<unknown>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const response = await fetchOrdersTrend();

        if (!active) return;

        setRaw(response);

        if (
          isRecord(response) &&
          response.success === false
        ) {
          throw new Error("Orders trend API error");
        }

        const normalized = normalizeTrend(response);

        if (normalized.length === 0) {
          throw new Error(
            "API yanıtındaki tarih ve sipariş alanları tanınamadı."
          );
        }

        setData(normalized);
      } catch (err) {
        if (!active) return;

        setError(
          err instanceof Error
            ? err.message
            : "Trend verisi alınamadı."
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="panel trend-panel">
      <div className="panel-heading">
        <div>
          <h2>Orders Trend</h2>
          <p>
            Order volume over time · Synthetic dates
          </p>
        </div>

        <span className="filter-count">
          All data
        </span>
      </div>

      {loading ? (
        <p className="empty-message">
          Loading order trends...
        </p>
      ) : error ? (
        <div>
          <p role="alert" className="error-banner">
            {error}
          </p>

          <details className="debug-details">
            <summary>Inspect API response</summary>
            <pre>
              {JSON.stringify(raw, null, 2)}
            </pre>
          </details>
        </div>
      ) : (
        <div className="trend-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{
                top: 12,
                right: 18,
                left: 0,
                bottom: 8,
              }}
            >
              <CartesianGrid
                stroke="#e8edf4"
                strokeDasharray="4 4"
                vertical={false}
              />

              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                minTickGap={35}
              />

              <YAxis
                tick={{ fontSize: 11 }}
                width={55}
              />

              <Tooltip
                formatter={(value) => [
                  Number(value).toLocaleString("en-US"),
                  "Orders",
                ]}
              />
                <Legend verticalAlign="top" height={36} />
              <Line
                type="monotone"
                dataKey="orders"
                stroke="#169b7a"
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 5 }}
              />

              <Line
                type="monotone"
                dataKey="customers"
                name="Customers"
                stroke="#6366f1"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5 }}
            />
              
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
