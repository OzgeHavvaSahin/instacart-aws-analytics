import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  fetchFilters,
  fetchOverview,
} from "./api/analytics";

import type {
  FiltersData,
  OverviewData,
  OverviewFilters,
} from "./types/analytics";

import "./App.css";

import OrdersTrendChart from "./components/OrdersTrendChart";

type FormFilters = {
  department_id: string;
  aisle_id: string;
  date_from: string;
  date_to: string;
  reordered: string;
};

type Metric = {
  key: string;
  value: number;
};

const emptyFilters: FormFilters = {
  department_id: "",
  aisle_id: "",
  date_from: "",
  date_to: "",
  reordered: "",
};

const numberFormat = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

function toApiFilters(
  form: FormFilters
): OverviewFilters {
  return {
    ...(form.department_id && {
      department_id: Number(form.department_id),
    }),
    ...(form.aisle_id && {
      aisle_id: Number(form.aisle_id),
    }),
    ...(form.date_from && {
      date_from: form.date_from,
    }),
    ...(form.date_to && {
      date_to: form.date_to,
    }),
    ...(form.reordered !== "" && {
      reordered: form.reordered === "true",
    }),
  };
}

// API'den gelen gerçek sayısal alanları bul.
function collectMetrics(
  value: unknown,
  prefix = "",
  depth = 0
): Metric[] {
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    depth > 3
  ) {
    return [];
  }

  const result: Metric[] = [];

  for (const [key, entry] of Object.entries(value)) {
    const path = prefix
      ? `${prefix}.${key}`
      : key;

    if (
      typeof entry === "number" &&
      Number.isFinite(entry)
    ) {
      result.push({
        key: path,
        value: entry,
      });
    } else if (
      entry &&
      typeof entry === "object" &&
      !Array.isArray(entry)
    ) {
      result.push(
        ...collectMetrics(entry, path, depth + 1)
      );
    }
  }

  return result;
}

function labelOf(key: string) {
  return key
    .split(".")
    .pop()!
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}


function formatMetric(metric: Metric) {
  if (metric.key === "estimated_revenue") {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(metric.value);
  }

  if (metric.key === "reorder_rate") {
    return `${metric.value.toFixed(2)}%`;
  }

  if (metric.key === "avg_basket_size") {
    return metric.value.toFixed(2);
  }

  return new Intl.NumberFormat("en-US").format(
    metric.value
  );
}


const priority = [
  "total_revenue",
  "revenue",
  "total_orders",
  "order_count",
  "total_customers",
  "unique_customers",
  "total_users",
  "total_items",
  "avg_order_value",
  "average_order_value",
  "reorder_rate",
];

function prioritizeMetrics(metrics: Metric[]) {
  return [...metrics].sort((a, b) => {
    const score = (key: string) => {
      const leaf = key
        .split(".")
        .pop()!
        .toLowerCase();

      const index = priority.indexOf(leaf);

      return index < 0
        ? priority.length
        : index;
    };

    return score(a.key) - score(b.key);
  });
}

export default function App() {
  const [filtersData, setFiltersData] =
    useState<FiltersData | null>(null);

  const [form, setForm] =
    useState<FormFilters>(emptyFilters);

  const [overview, setOverview] =
    useState<OverviewData | null>(null);

  const [filtersLoading, setFiltersLoading] =
    useState(true);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [appliedParams, setAppliedParams] =
    useState<OverviewFilters>({});

  const [lastUpdated, setLastUpdated] =
    useState<string | null>(null);

  const filterRequestId = useRef(0);
  const overviewRequestId = useRef(0);

  // Overview verilerini getir.
  const loadOverview = useCallback(
    async (params: OverviewFilters) => {
      const requestId =
        ++overviewRequestId.current;

      setLoading(true);
      setError(null);

      try {
        const response =
          await fetchOverview(params);

        if (
          requestId !== overviewRequestId.current
        ) {
          return;
        }

        if (!response.success) {
          throw new Error(
            "Overview API returned an error"
          );
        }

        setOverview(response.data);
        setAppliedParams(params);

        setLastUpdated(
          new Date().toLocaleTimeString("tr-TR")
        );
      } catch (err) {
        if (
          requestId === overviewRequestId.current
        ) {
          setError(
            err instanceof Error
              ? err.message
              : "Overview error"
          );
        }
      } finally {
        if (
          requestId === overviewRequestId.current
        ) {
          setLoading(false);
        }
      }
    },
    []
  );

  // Sayfa ilk açıldığında yükle.
  useEffect(() => {
    let mounted = true;

    fetchFilters()
      .then((result) => {
        if (mounted) {
          setFiltersData(result.data);
        }
      })
      .catch((err: unknown) => {
        if (mounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Filter error"
          );
        }
      })
      .finally(() => {
        if (mounted) {
          setFiltersLoading(false);
        }
      });

    void loadOverview({});

    return () => {
      mounted = false;
      overviewRequestId.current++;
      filterRequestId.current++;
    };
  }, [loadOverview]);

  // Department değişince aisle listesini güncelle.
  async function handleDepartmentChange(
    value: string
  ) {
    setForm((previous) => ({
      ...previous,
      department_id: value,
      aisle_id: "",
    }));

    setError(null);

    const requestId =
      ++filterRequestId.current;

    setFiltersLoading(true);

    try {
      const result = await fetchFilters(
        value ? Number(value) : undefined
      );

      if (
        requestId === filterRequestId.current
      ) {
        setFiltersData(result.data);
      }
    } catch (err) {
      if (
        requestId === filterRequestId.current
      ) {
        setError(
          err instanceof Error
            ? err.message
            : "Filter error"
        );
      }
    } finally {
      if (
        requestId === filterRequestId.current
      ) {
        setFiltersLoading(false);
      }
    }
  }

  function applyFilters() {
    if (
      form.date_from &&
      form.date_to &&
      form.date_from > form.date_to
    ) {
      setError(
        "Başlangıç tarihi bitiş tarihinden büyük olamaz."
      );
      return;
    }

    void loadOverview(toApiFilters(form));
  }

  function resetFilters() {
    setForm({ ...emptyFilters });
    setError(null);

    void handleDepartmentChange("");
    void loadOverview({});
  }


const metrics: Metric[] = overview
  ? [
      {
        key: "total_orders",
        value: overview.total_orders,
      },
      {
        key: "total_customers",
        value: overview.total_customers,
      },
      {
        key: "total_items",
        value: overview.total_items,
      },
      {
        key: "estimated_revenue",
        value: overview.estimated_revenue,
      },
      {
        key: "avg_basket_size",
        value: overview.avg_basket_size,
      },
      {
        key: "reorder_rate",
        value: overview.reorder_rate,
      },
    ]
  : [];


  const activeCount =
    Object.keys(appliedParams).length;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">◈</span>

          <div>
            Instacart
            <span>Analytics Platform</span>
          </div>
        </div>

        <div className="nav-caption">
          WORKSPACE
        </div>

        <div className="nav-item selected">
          ▦ <span>Overview</span>
        </div>

        <div className="nav-item muted">
          ◷ <span>Analytics modules — next phase</span>
        </div>

        <div className="sidebar-foot">
          Data source
          <strong>Amazon Athena</strong>
          <small>
            Orders · Products · Customers
          </small>
        </div>
      </aside>

      <main className="main-content">
        <header className="header">
          <div>
            <p className="eyebrow">
              ECOMMERCE INTELLIGENCE
            </p>

            <h1>Analytics Overview</h1>

            <p className="subheading">
              Explore purchasing behavior and
              performance using global filters.
            </p>
          </div>

          <span className="source-badge">
            ● Athena API
          </span>
        </header>

        <section className="panel filter-panel">
          <div className="panel-heading">
            <div>
              <h2>Global filters</h2>

              <p>
                Apply filters to refresh the
                full overview.
              </p>
            </div>

            <span className="filter-count">
              {activeCount} active
            </span>
          </div>

          <div className="filter-grid">
            <label>
              Department

              <select
                value={form.department_id}
                onChange={(e) =>
                  void handleDepartmentChange(
                    e.target.value
                  )
                }
              >
                <option value="">
                  All Departments
                </option>

                {filtersData?.departments.map(
                  (department) => (
                    <option
                      key={department.id}
                      value={department.id}
                    >
                      {department.name}
                    </option>
                  )
                )}
              </select>
            </label>

            <label>
              Aisle

              <select
                value={form.aisle_id}
                disabled={filtersLoading}
                onChange={(e) =>
                  setForm((previous) => ({
                    ...previous,
                    aisle_id: e.target.value,
                  }))
                }
              >
                <option value="">
                  All Aisles
                </option>

                {filtersData?.aisles.map(
                  (aisle) => (
                    <option
                      key={aisle.id}
                      value={aisle.id}
                    >
                      {aisle.name}
                    </option>
                  )
                )}
              </select>
            </label>

            <label>
              From date
              <span className="helper">
                {" "}(synthetic)
              </span>

              <input
                type="date"
                value={form.date_from}
                min={
                  filtersData?.date_range.min ??
                  undefined
                }
                max={
                  filtersData?.date_range.max ??
                  undefined
                }
                onChange={(e) =>
                  setForm((previous) => ({
                    ...previous,
                    date_from: e.target.value,
                  }))
                }
              />
            </label>

            <label>
              To date
              <span className="helper">
                {" "}(synthetic)
              </span>

              <input
                type="date"
                value={form.date_to}
                min={
                  filtersData?.date_range.min ??
                  undefined
                }
                max={
                  filtersData?.date_range.max ??
                  undefined
                }
                onChange={(e) =>
                  setForm((previous) => ({
                    ...previous,
                    date_to: e.target.value,
                  }))
                }
              />
            </label>

            <label>
              Purchase type

              <select
                value={form.reordered}
                onChange={(e) =>
                  setForm((previous) => ({
                    ...previous,
                    reordered: e.target.value,
                  }))
                }
              >
                <option value="">
                  All purchases
                </option>

                <option value="true">
                  Reordered
                </option>

                <option value="false">
                  First-time purchase
                </option>
              </select>
            </label>
          </div>

          <div className="filter-actions">
            <span className="loading-caption">
              {filtersLoading
                ? "Loading filter options…"
                : loading
                ? "Querying Athena…"
                : lastUpdated
                ? `Updated at ${lastUpdated}`
                : "Ready"}
            </span>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={resetFilters}
              disabled={loading}
            >
              Reset
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={applyFilters}
              disabled={
                loading || filtersLoading
              }
            >
              {loading
                ? "Loading…"
                : "Apply filters"}
            </button>
          </div>
        </section>

        {error && (
          <div
            className="error-banner"
            role="alert"
          >
            {error}
          </div>
        )}

        <section className="dashboard-section">
          <div className="section-title">
            <div>
              <h2>
                Key performance indicators
              </h2>

              <p>
                Metrics returned by the overview
                API. Synthetic prices and dates
                where applicable.
              </p>
            </div>
          </div>

          <div className="kpi-grid">
            {metrics.length ? (
              metrics
                .slice(0, 8)
                .map((metric) => (
                  <article
                    key={metric.key}
                    className="kpi-card"
                  >
                    <div className="kpi-label">
                      {labelOf(metric.key)}
                    </div>

                    <strong className="kpi-value">
                      {formatMetric(metric)}
                    </strong>

                    <small title={metric.key}>
                      {metric.key}
                    </small>
                  </article>
                ))
            ) : (
              <div className="empty-card">
                {loading
                  ? "Loading overview KPIs…"
                  : "No numeric KPIs returned. Inspect the API response below."}
              </div>
            )}
          </div>
        </section>

        <OrdersTrendChart />

        <section className="panel detail-panel">
          <div className="panel-heading">
            <div>
              <h2>Metric details</h2>

              <p>
                All numeric overview metrics.
                No placeholder data.
              </p>
            </div>

            <span className="filter-count">
              {metrics.length} metrics
            </span>
          </div>

          {metrics.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>API field</th>
                    <th>Value</th>
                  </tr>
                </thead>

                <tbody>
                  {metrics.map((metric) => (
                    <tr key={metric.key}>
                      <td>
                        {labelOf(metric.key)}
                      </td>

                      <td className="api-field">
                        {metric.key}
                      </td>

                      <td className="value-cell">
                        {formatMetric(metric)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty-message">
              Awaiting analytics data.
            </p>
          )}
        </section>

        <details className="debug-details">
          <summary>
            Developer diagnostics: API
            response and applied parameters
          </summary>

          <h3>Applied parameters</h3>

          <pre>
            {JSON.stringify(
              appliedParams,
              null,
              2
            )}
          </pre>

          <h3>Overview response</h3>

          <pre>
            {JSON.stringify(
              overview,
              null,
              2
            )}
          </pre>
        </details>

        <footer>
          Instacart Market Basket Analysis
          · Synthetic pricing/date enrichment
          · AWS Athena
        </footer>
      </main>
    </div>
  );
}
