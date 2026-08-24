import { useParams } from "react-router-dom";
import { Card } from "../lib/components";
import { useTimeline } from "../hooks/useTimeline";
import { useSnapshotId } from "../hooks/useJob";
import { formatDate } from "../lib/format";
import { ErrorState, LoadingState } from "../components/StateViews";

export const TimelinePage = () => {
  const { id: projectId } = useParams<{ id: string }>();
  const { snapshotId, loading: snapLoading } = useSnapshotId(projectId);

  const { data, isLoading, isError, error, refetch } = useTimeline(snapshotId);

  if (snapLoading || isLoading) return <LoadingState />;
  if (!snapshotId) return <div className="p-8">No analysis snapshot available for this project yet.</div>;
  if (isError) return <ErrorState message={(error as Error).message} onRetry={() => refetch()} />;

  const events = data ?? [];

  return (
    <div className="min-h-screen bg-pageBg p-4 md:p-8">
      <h1 className="text-2xl font-bold text-slate-700 mb-6">Timeline</h1>

      {events.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map((event) => (
            <Card key={event.id} className="p-4">
              <div className="flex items-start">
                <div className="w-8 h-8 rounded-md bg-lavenderSoft flex items-center justify-center flex-shrink-0">
                  <span className="text-lavenderPrimary font-small">{event.type.slice(0, 2)}</span>
                </div>
                <div className="ml-3 flex-1">
                  <p className="font-medium text-slate-700">{event.title || "Unknown Event"}</p>
                  <p className="text-slate-500 text-sm">{event.summary || ""}</p>
                  <p className="text-xs text-slate-400">{formatDate(event.occurred_at) || ""}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <p className="text-slate-500 mb-6">No timeline events found for this snapshot.</p>
      )}
    </div>
  );
};

export default TimelinePage;