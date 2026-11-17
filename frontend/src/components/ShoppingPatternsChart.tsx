import type {
  OverviewFilters,
  ShoppingPoint,
} from "../types/analytics";

import { makeQuery } from "../api/analytics";

import { useAnalytics } from "../hooks/useAnalytics";

type Props = {
  filters: OverviewFilters;
};

const days = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const number = new Intl.NumberFormat("en-US");

export default function ShoppingPatternsChart({
  filters,
}: Props) {
  const query = makeQuery(filters);

  const { data, loading, error } = useAnalytics<{
    items: ShoppingPoint[];
  }>(`/api/analytics/shopping-patterns?${query}`);

  const items = data?.items ?? [];

  const counts = new Map(
    items.map((item) => [
      `${item.day_of_week}-${item.hour_of_day}`,
      item.total_orders,
    ])
  );

  const maxOrders = Math.max(
    0,
    ...items.map((item) => item.total_orders)
  );

  return (
    <section className="panel analytics-panel">
      <div className="panel-heading">
        <div>
          <h2>Shopping Patterns</h2>
          <p>Order activity by weekday and hour</p>
        </div>
      </div>

      {loading && (
        <p className="empty-message">
          Loading shopping patterns...
        </p>
      )}

      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && items.length === 0 && (
        <p className="empty-message">
          No shopping activity found.
        </p>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="heatmap-scroll">
          <div className="heatmap-grid">
            <div className="heatmap-row">
              <span />

              {Array.from(
                { length: 24 },
                (_, hour) => (
                  <span
                    className="heatmap-hour"
                    key={hour}
                  >
                    {hour}
                  </span>
                )
              )}
            </div>

            {days.map((day, dayIndex) => (
              <div
                className="heatmap-row"
                key={day}
              >
                <span className="heatmap-day">
                  {day.slice(0, 3)}
                </span>

                {Array.from(
                  { length: 24 },
                  (_, hour) => {
                    const count =
                      counts.get(
                        `${dayIndex + 1}-${hour}`
                      ) ?? 0;

                    const intensity =
                      maxOrders > 0
                        ? count / maxOrders
                        : 0;

                    return (
                      <div
                        className="heatmap-cell"
                        key={hour}
                        title={
                          `${day} ${String(hour).padStart(2, "0")}:00` +
                          ` — ${number.format(count)} orders`
                        }
                        style={{
                          backgroundColor:
                            `rgba(22,155,122,${0.08 + intensity * 0.92})`,
                        }}
                      />
                    );
                  }
                )}
              </div>
            ))}
          </div>

          <p className="heatmap-caption">
            Darker cells indicate more orders.
            Hover over a cell to view the count.
          </p>
        </div>
      )}
    </section>
  );
}
