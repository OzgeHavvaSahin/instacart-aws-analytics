
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

// Chart components
import OrdersTrendChart from "./components/OrdersTrendChart";
import TopProductsChart from "./components/TopProductsChart";
import RevenueTrendChart from "./components/RevenueTrendChart";
import DepartmentPerformanceChart from "./components/DepartmentPerformanceChart";
import ReorderAnalysisChart from "./components/ReorderAnalysisChart";
import ShoppingPatternsChart from "./components/ShoppingPatternsChart";

// Styles
import "./App.css";
import "./components/AnalyticsCharts.css";

// =====================================
// TYPES
// =====================================

type FormFilters = {
  department_id: string;
  aisle_id: string;
  date_from: string;
  date_to: string;
  reordered: string;
};

type Metric = {
  key: string;
  label: string;
  value: number;
};

// =====================================
// CONSTANTS
// =====================================

const emptyFilters: FormFilters = {
  department_id: "",
  aisle_id: "",
  date_from: "",
  date_to: "",
  reordered: "",
};

const integerFormatter = new Intl.NumberFormat(
  "en-US"
);

const currencyFormatter = new Intl.NumberFormat(
  "en-US",
  {
    style: "currency",
    currency: "USD",
  }
);

// =====================================
// HELPERS
// =====================================

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

function formatMetric(metric: Metric): string {
  switch (metric.key) {
    case "estimated_revenue":
      return currencyFormatter.format(metric.value);

    case "reorder_rate":
      return `${metric.value.toFixed(2)}%`;

    case "avg_basket_size":
      return metric.value.toFixed(2);

    default:
      return integerFormatter.format(metric.value);
  }
}

function createMetrics(
  overview: OverviewData | null
): Metric[] {
  if (!overview) {
    return [];
  }

  return [
    {
      key: "total_orders",
      label: "Total Orders",
      value: overview.total_orders,
    },
    {
      key: "total_customers",
      label: "Total Customers",
      value: overview.total_customers,
    },
    {
      key: "total_items",
      label: "Total Items",
      value: overview.total_items,
    },
    {
      key: "estimated_revenue",
      label: "Estimated Revenue",
      value: overview.estimated_revenue,
    },
    {
      key: "avg_basket_size",
      label: "Average Basket Size",
      value: overview.avg_basket_size,
    },
    {
      key: "reorder_rate",
      label: "Reorder Rate",
      value: overview.reorder_rate,
    },
  ];
}

// =====================================
// MAIN APPLICATION
// =====================================

export default function App() {
  // -----------------------------------
  // STATE
  // -----------------------------------

  const [filtersData, setFiltersData] =
    useState<FiltersData | null>(null);

  const [form, setForm] =
    useState<FormFilters>({ ...emptyFilters });

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

  const overviewRequestId = useRef(0);

  // -----------------------------------
  // OVERVIEW API
  // -----------------------------------

  const loadOverview = useCallback(
    async (params: OverviewFilters) => {
      const requestId =
        ++overviewRequestId.current;

      setLoading(true);
      setError(null);

      try {
        const response = await fetchOverview(params);

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
          requestId !== overviewRequestId.current
        ) {
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Overview data could not be loaded"
        );
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

  // -----------------------------------
  // INITIAL DATA LOADING
  // -----------------------------------

  useEffect(() => {
    let mounted = true;

    async function loadInitialFilters() {
      setFiltersLoading(true);

      try {
        // Fetch all department-aisle
        // relationships once.
        const response = await fetchFilters();

        if (!mounted) {
          return;
        }

        if (!response.success) {
          throw new Error(
            "Filters API returned an error"
          );
        }

        setFiltersData(response.data);
      } catch (err) {
        if (!mounted) {
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Filter options could not be loaded"
        );
      } finally {
        if (mounted) {
          setFiltersLoading(false);
        }
      }
    }

    void loadInitialFilters();
    void loadOverview({});

    return () => {
      mounted = false;
      overviewRequestId.current++;
    };
  }, [loadOverview]);

  // -----------------------------------
  // DEPARTMENT / AISLE FILTERING
  // -----------------------------------

  function handleDepartmentChange(value: string) {
    setForm((previous) => ({
      ...previous,
      department_id: value,
      aisle_id: "",
    }));
  }

  const visibleAisles = (
    filtersData?.aisles ?? []
  ).filter(
    (aisle) =>
      form.department_id === "" ||
      aisle.department_id ===
        Number(form.department_id)
  );

  // -----------------------------------
  // APPLY FILTERS
  // -----------------------------------

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

    const params = toApiFilters(form);

    void loadOverview(params);
  }

  // -----------------------------------
  // RESET FILTERS
  // -----------------------------------

  function resetFilters() {
    setForm({ ...emptyFilters });
    setError(null);

    void loadOverview({});
  }

  // -----------------------------------
  // DERIVED DATA
  // -----------------------------------

  const metrics = createMetrics(overview);

  const activeCount = Object.values(
    appliedParams
  ).filter(
    (value) =>
      value !== undefined &&
      value !== null &&
      value !== ""
  ).length;

  // -----------------------------------
  // RENDER
  // -----------------------------------

  return (
    <div className="app-shell">
      {/* SIDEBAR */}

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
          ◷ <span>Advanced Analytics</span>
        </div>

        <div className="sidebar-foot">
          Data source

          <strong>Amazon Athena</strong>

          <small>
            Orders · Products · Customers
          </small>
        </div>
      </aside>

      {/* MAIN CONTENT */}

      <main className="main-content">
        {/* HEADER */}

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

        {/* GLOBAL FILTERS */}

        <section className="panel filter-panel">
          <div className="panel-heading">
            <div>
              <h2>Global Filters</h2>

              <p>
                Apply filters to refresh analytics.
              </p>
            </div>

            <span className="filter-count">
              {activeCount} active
            </span>
          </div>

          <div className="filter-grid">
            {/* DEPARTMENT */}

            <label>
              Department

              <select
                value={form.department_id}
                disabled={filtersLoading}
                onChange={(event) =>
                  handleDepartmentChange(
                    event.target.value
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

            {/* AISLE */}

            <label>
              Aisle

              <select
                value={form.aisle_id}
                disabled={filtersLoading}
                onChange={(event) =>
                  setForm((previous) => ({
                    ...previous,
                    aisle_id: event.target.value,
                  }))
                }
              >
                <option value="">
                  All Aisles
                </option>

                {visibleAisles.map((aisle) => (
                  <option
                    key={aisle.id}
                    value={aisle.id}
                  >
                    {aisle.name}
                  </option>
                ))}
              </select>
            </label>

            {/* DATE FROM */}

            <label>
              From Date

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
                onChange={(event) =>
                  setForm((previous) => ({
                    ...previous,
                    date_from: event.target.value,
                  }))
                }
              />
            </label>

            {/* DATE TO */}

            <label>
              To Date

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
                onChange={(event) =>
                  setForm((previous) => ({
                    ...previous,
                    date_to: event.target.value,
                  }))
                }
              />
            </label>

            {/* PURCHASE TYPE */}

            <label>
              Purchase Type

              <select
                value={form.reordered}
                onChange={(event) =>
                  setForm((previous) => ({
                    ...previous,
                    reordered: event.target.value,
                  }))
                }
              >
                <option value="">
                  All Purchases
                </option>

                <option value="true">
                  Reordered
                </option>

                <option value="false">
                  First-time Purchase
                </option>
              </select>
            </label>
          </div>

          {/* FILTER ACTIONS */}

          <div className="filter-actions">
            <span className="loading-caption">
              {filtersLoading
                ? "Loading filter options..."
                : loading
                ? "Querying Athena..."
                : lastUpdated
                ? `Updated at ${lastUpdated}`
                : "Ready"}
            </span>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={resetFilters}
              disabled={loading || filtersLoading}
            >
              Reset
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={applyFilters}
              disabled={loading || filtersLoading}
            >
              {loading
                ? "Loading..."
                : "Apply Filters"}
            </button>
          </div>
        </section>

        {/* ERROR */}

        {error && (
          <div
            className="error-banner"
            role="alert"
          >
            {error}
          </div>
        )}

        {/* KPI SECTION */}

        <section className="dashboard-section">
          <div className="section-title">
            <div>
              <h2>
                Key Performance Indicators
              </h2>

              <p>
                Overview of order, customer,
                revenue and purchase metrics.
              </p>
            </div>
          </div>

          <div className="kpi-grid">
            {metrics.length > 0 ? (
              metrics.map((metric) => (
                <article
                  key={metric.key}
                  className="kpi-card"
                >
                  <div className="kpi-label">
                    {metric.label}
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
                  ? "Loading overview KPIs..."
                  : "No overview data available."}
              </div>
            )}
          </div>
        </section>

        {/* ORDERS TREND */}

        <OrdersTrendChart />

        {/* ADVANCED ANALYTICS */}

        <section className="analytics-section">
          <div className="analytics-section-title">
            <h2>Advanced Analytics</h2>

            <p>
              Explore product, revenue and
              shopping performance.
            </p>
          </div>

          <div className="analytics-grid">
            <RevenueTrendChart
              filters={appliedParams}
            />

            <TopProductsChart
              filters={appliedParams}
            />

            <DepartmentPerformanceChart
              filters={appliedParams}
            />

            <ReorderAnalysisChart
              filters={appliedParams}
            />
          </div>
        </section>

        {/* SHOPPING PATTERNS */}

        <section className="analytics-section">
          <ShoppingPatternsChart
            filters={appliedParams}
          />
        </section>

        {/* METRIC DETAILS */}

        <section className="panel detail-panel">
          <div className="panel-heading">
            <div>
              <h2>Metric Details</h2>

              <p>
                Detailed overview metrics.
              </p>
            </div>

            <span className="filter-count">
              {metrics.length} metrics
            </span>
          </div>

          {metrics.length > 0 ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>API Field</th>
                    <th>Value</th>
                  </tr>
                </thead>

                <tbody>
                  {metrics.map((metric) => (
                    <tr key={metric.key}>
                      <td>{metric.label}</td>

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

        {/* DEVELOPER DIAGNOSTICS */}

        <details className="debug-details">
          <summary>
            Developer diagnostics:
            API response and applied parameters
          </summary>

          <h3>Applied Parameters</h3>

          <pre>
            {JSON.stringify(
              appliedParams,
              null,
              2
            )}
          </pre>

          <h3>Overview Response</h3>

          <pre>
            {JSON.stringify(
              overview,
              null,
              2
            )}
          </pre>
        </details>

        {/* FOOTER */}

        <footer>
          Instacart Market Basket Analysis
          · AWS Athena Analytics
        </footer>
      </main>
    </div>
  );
}
