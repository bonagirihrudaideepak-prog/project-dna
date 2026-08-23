import { useParams } from "react-router-dom";
import { ScoreCard } from "../lib/components";
import { useDNA } from "../hooks/useDNA";
import { useSnapshotId } from "../hooks/useJob";
import { ErrorState, LoadingState } from "../components/StateViews";

export const DNAPage = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const { snapshotId, loading: snapLoading } = useSnapshotId(projectId);

  const { data, isLoading, isError, error, refetch } = useDNA(snapshotId);

  if (snapLoading || isLoading) return <LoadingState />;
  if (!snapshotId) return <div className="p-8">No analysis snapshot available for this project yet.</div>;
  if (isError) return <ErrorState message={(error as Error).message} onRetry={() => refetch()} />;

  const scores = data ?? [];

  return (
    <div className="min-h-screen bg-pageBg p-4 md:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-700">DNA Analysis</h1>
        <p className="text-slate-500 text-sm">Eight explainable dimensions with evidence drill-down.</p>
      </header>

      {scores.length === 0 ? (
        <p className="text-slate-500">No scores recorded for this snapshot.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {scores.map((d) => (
            <ScoreCard
              key={d.dimension}
              dimension={d.dimension}
              score={d.score ?? undefined}
              coverage={d.coverage || 0}
              confidence={(d.confidence as ScoreCardConfidence) || "insufficient"}
              direction={d.direction === "lower_is_better" ? "lower_is_better" : "higher_is_better"}
              limitations={(d.explanation?.limitations as string[]) || []}
            />
          ))}
        </div>
      )}
    </div>
  );
};

type ScoreCardConfidence = "insufficient" | "low" | "moderate" | "high";

export default DNAPage;