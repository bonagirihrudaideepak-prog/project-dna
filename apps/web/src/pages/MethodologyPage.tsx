import { PageHeader } from "../components/ProjectSelector";
import { LoadingState, ErrorState } from "../components/StateViews";
import { useMethodology } from "../hooks/useMethodology";
import { C, FONT_MONO, panelStyle, gradientBannerStyle } from "../lib/ui";

const directionLabel = (d: string) =>
  d === "lower_is_better" ? "lower → better" : d === "descriptive" ? "descriptive" : "higher → better";

export default function MethodologyPage() {
  const { data, isLoading, isError, error, refetch } = useMethodology();

  if (isLoading) return <LoadingState />;
  if (isError || !data) {
    return (
      <div className="max-w-screen-xl mx-auto px-6 py-8">
        <ErrorState
          message={(error as Error | null)?.message ?? "Failed to load methodology."}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-8">
      <PageHeader title="Methodology" subtitle="How Project DNA scores and evaluates repositories" />

      {/* Overview */}
      <div className="rounded-xl p-6 mb-6" style={gradientBannerStyle}>
        <h2 style={{ fontSize: "16px", fontWeight: 700, color: C.ink, marginBottom: "12px" }}>
          The 8-Dimension Framework
        </h2>
        <p style={{ fontSize: "13px", color: "#475569", lineHeight: 1.7, maxWidth: "680px" }}>
          Each dimension is scored independently as{" "}
          <span style={{ fontFamily: FONT_MONO }}>round(100·Σwᵢqᵢxᵢ / Σwᵢqᵢ)</span> — a weighted,
          quality-adjusted mean of its indicators. A score is <strong>withheld (never zeroed)</strong>{" "}
          when indicator coverage falls below{" "}
          <span style={{ fontFamily: FONT_MONO }}>{data.min_coverage_for_score}</span>. Dimensions marked{" "}
          <em>lower is better</em> are inverted when computing the overall DNA score.
        </p>
        <p style={{ fontSize: "11px", fontFamily: FONT_MONO, color: C.lavender, marginTop: "10px", marginBottom: 0 }}>
          model version: {data.model_version}
        </p>
      </div>

      {/* Dimension details */}
      <div className="grid gap-4 md:grid-cols-2">
        {data.dimensions.map((d, i) => (
          <div key={d.key} className="rounded-xl p-5" style={panelStyle}>
            <div className="flex items-start gap-4">
              <div className="flex items-center justify-center rounded-lg flex-shrink-0" style={{ width: "36px", height: "36px", backgroundColor: C.lavenderSoft }}>
                <span style={{ fontFamily: FONT_MONO, fontSize: "13px", fontWeight: 700, color: C.lavender }}>
                  {String(i + 1).padStart(2, "0")}
                </span>
              </div>
              <div className="min-w-0">
                <h3 style={{ fontSize: "13px", fontWeight: 600, color: C.ink, marginBottom: "4px" }}>{d.name}</h3>
                <p style={{ fontSize: "12px", color: C.muted, lineHeight: 1.6, marginBottom: "8px" }}>{d.description}</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <span style={{ fontSize: "11px", color: C.faint, fontFamily: FONT_MONO }}>{directionLabel(d.direction)}</span>
                  <span style={{ width: "3px", height: "3px", borderRadius: "50%", backgroundColor: "#cbd5e1", display: "inline-block" }} />
                  <span style={{ fontSize: "11px", color: C.faint }}>{d.indicators.length} indicators</span>
                </div>

                {/* Indicators table */}
                <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "10px" }}>
                  <tbody>
                    {d.indicators.map((ind) => (
                      <tr key={ind.key}>
                        <td style={{ padding: "3px 0", fontSize: "11px", color: C.body, fontFamily: FONT_MONO }}>{ind.key}</td>
                        <td style={{ padding: "3px 0", fontSize: "11px", color: C.faint, textAlign: "right", fontFamily: FONT_MONO }}>
                          w {ind.weight.toFixed(2)}
                        </td>
                        <td style={{ padding: "3px 0 3px 10px", fontSize: "10px", color: C.faint, textAlign: "right", whiteSpace: "nowrap" }}>
                          {directionLabel(ind.direction)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Confidence levels */}
      <div className="mt-6 rounded-xl p-5" style={panelStyle}>
        <h2 style={{ fontSize: "14px", fontWeight: 600, color: C.ink, marginBottom: "16px" }}>Confidence Levels</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {data.coverage_labels.map((item) => (
            <div key={item.label} className="p-4 rounded-lg" style={{ backgroundColor: C.pageBg, border: `1px solid ${C.borderLight}` }}>
              <div style={{ fontSize: "12px", fontWeight: 600, color: C.ink, textTransform: "capitalize", marginBottom: "4px" }}>
                {item.label}
              </div>
              <p style={{ fontSize: "11px", color: C.muted, lineHeight: 1.5, marginBottom: 0 }}>
                coverage below {Math.round(item.below * 100)}%
              </p>
            </div>
          ))}
        </div>

        {/* Coverage threshold visual */}
        <div className="mt-5">
          <div style={{ display: "flex", height: 14, borderRadius: 7, overflow: "hidden", border: `1px solid ${C.border}` }}>
            {data.coverage_labels.map((c, i) => {
              const prev = i === 0 ? 0 : data.coverage_labels[i - 1].below * 100;
              const width = Math.max(0, c.below * 100 - prev);
              const bg = ["#ef4444", "#f59e0b", "#f97316", "#10b981"][i] ?? C.border;
              return <div key={c.label} title={`${c.label}: coverage < ${Math.round(c.below * 100)}%`} style={{ width: `${width}%`, background: bg, opacity: 0.85 }} />;
            })}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
            {data.coverage_labels.map((c) => (
              <span key={c.label} style={{ fontSize: "11px", color: C.faint }}>
                {c.label} · &lt;{Math.round(c.below * 100)}%
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Caveats */}
      {data.caveats.length > 0 && (
        <div className="mt-6 rounded-xl p-5" style={gradientBannerStyle}>
          <h2 style={{ fontSize: "13px", fontWeight: 600, color: C.ink, marginBottom: "8px" }}>Caveats</h2>
          <ul className="space-y-2">
            {data.caveats.map((caveat) => (
              <li key={caveat} style={{ fontSize: "12px", color: "#475569" }}>
                • {caveat}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
