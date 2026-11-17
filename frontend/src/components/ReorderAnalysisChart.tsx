
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";

import type { OverviewFilters } from "../types/analytics";
import {
  makeQuery,
  type ReorderData,
} from "../api/dashboard";
import { useAnalytics } from "../hooks/useAnalytics";

type Props = {
  filters: OverviewFilters;
};

const colors = ["#169b7a", "#dcece8"];

const number = new Intl.NumberFormat("en-US");

export default function ReorderAnalysisChart({
  filters,
}: Props) {
  const query = makeQuery(filters);

  const { data, loading, error } =
    useAnalytics<ReorderData>(
      `/api/analytics/reorders?${query}`
    );

  const segments = data
    ? [
        {
          name: "Reordered",
          value: data.reordered_items,
        },
        {
          name: "First-time",
          value: data.first_time_items,
        },
      ]
    : [];

  return (
    <section className="panel analytics-panel">
      <div className="panel-heading">
        <div>
          <h2>Reorder Analysis</h2>
          <p>Repeat and first-time purchases</p>
        </div>
      </div>

      {loading && (
        <p className="empty-message">
          Loading reorder analysis...
        </p>
      )}

      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && data?.total_items === 0 && (
        <p className="empty-message">
          No purchase data found.
        </p>
      )}

      {!loading &&
        !error &&
        data &&
        data.total_items > 0 && (
          <>
            <div className="analytics-chart donut-chart">
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <PieChart>
                  <Pie
                    data={segments}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={72}
                    outerRadius={108}
                    paddingAngle={3}
                  >
                    {segments.map((segment, index) => (
                      <Cell
                        key={segment.name}
                        fill={colors[index]}
                      />
                    ))}
                  </Pie>

                  <Tooltip
                    formatter={(value) =>
                      number.format(Number(value))
                    }
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="reorder-summary">
              <div>
                <span>Reordered Items</span>
                <strong>
                  {number.format(data.reordered_items)}
                </strong>
              </div>

              <div>
                <span>First-time Items</span>
                <strong>
                  {number.format(data.first_time_items)}
                </strong>
              </div>

              <div>
                <span>Reorder Rate</span>
                <strong>
                  {data.reorder_rate.toFixed(2)}%
                </strong>
              </div>
            </div>
          </>
        )}
    </section>
  );
}
