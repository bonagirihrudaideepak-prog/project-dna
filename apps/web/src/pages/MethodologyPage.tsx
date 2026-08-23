import { Card } from "../lib/components";
import { useMethodology } from "../hooks/useMethodology";
import { ErrorState, LoadingState } from "../components/StateViews";

const directionLabel = (d: string) =>
  d === "lower_is_better" ? "Lower is better" : d === "descriptive" ? "Descriptive" : "Higher is better";

export const MethodologyPage = () => {
  const { data, isLoading, isError, error, refetch } = useMethodology();

  if (isLoading) return <LoadingState />;
  if (isError || !data) {
    return (
      <ErrorState
        message={(error as Error | null)?.message ?? "Failed to load methodology."}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="min-h-screen bg-pageBg p-4 md:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-700">Scoring Methodology</h1>
        <p className="text-slate-500 text-sm">
          Model <strong>{data.model_version}</strong> · score = round(100·Σwᵢqᵢxᵢ / Σwᵢqᵢ) · withheld when
          coverage &lt; {data.min_coverage_for_score}
        </p>
      </header>

      {data.dimensions.map((dim) => (
        <Card key={dim.key} className="p-6 mb-4">
          <div className="row between wrap">
            <h3 className="text-lavenderPrimary">{dim.name}</h3>
            <span className="badge accent">{directionLabel(dim.direction)}</span>
          </div>
          <p className="muted small mt-1">{dim.description}</p>
          <table className="mt-3">
            <thead>
              <tr>
                <th>Indicator</th>
                <th style={{ width: 100 }}>Weight</th>
                <th>Direction</th>
              </tr>
            </thead>
            <tbody>
              {dim.indicators.map((ind) => (
                <tr key={ind.key}>
                  <td className="small">{ind.key}</td>
                  <td className="small">{ind.weight.toFixed(2)}</td>
                  <td className="small muted">{directionLabel(ind.direction)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ))}

      <Card className="p-6">
        <h3>Coverage labels</h3>
        <p className="muted small">
          {data.coverage_labels.map((c) => `${c.label} (< ${c.below})`).join(" · ")}
        </p>
        <ul className="mt-2 space-y-2">
          {data.caveats.map((caveat) => (
            <li key={caveat} className="muted small">
              • {caveat}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
};

export default MethodologyPage;
