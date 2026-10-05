import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Flag, RefreshCw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/api/endpoints";
import { useVideo } from "@/api/queries";
import { useAuth } from "@/auth/AuthProvider";
import { hasRole, REVIEWER_UP } from "@/auth/roles";
import { InspectionView } from "@/components/inspection/InspectionView";
import { ReviewHistory } from "@/components/review/ReviewHistory";
import { Button, Card, ErrorState, Skeleton, useToast } from "@/components/ui";

function DetailSkeleton() {
  return (
    <div aria-busy="true" className="grid gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
      <Skeleton className="aspect-video w-full" />
      <div className="grid gap-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}

export function VideoDetailPage() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const detail = useVideo(Number.isFinite(id) ? id : undefined);
  const qc = useQueryClient();
  const toast = useToast();
  const canReanalyze = hasRole(user, REVIEWER_UP);

  const reanalyze = useMutation({
    mutationFn: () => api.reanalyze(id),
    onSuccess: () => {
      toast("Re-analysis queued.");
      void qc.invalidateQueries({ queryKey: ["video", id] });
    },
    onError: (err) => toast(err instanceof Error ? err.message : "Couldn't queue it.", "error"),
  });

  const dispute = useMutation({
    mutationFn: (disputed: boolean) => api.setDisputed(id, disputed),
    onSuccess: (video) => {
      toast(video.disputed ? "Marked as disputed. The file is kept." : "Dispute cleared.");
      void qc.invalidateQueries({ queryKey: ["video", id] });
    },
    onError: (err) => toast(err instanceof Error ? err.message : "Couldn't update it.", "error"),
  });

  if (detail.isPending) return <DetailSkeleton />;
  if (detail.isError) {
    return (
      <Card>
        <ErrorState error={detail.error} onRetry={() => detail.refetch()} />
      </Card>
    );
  }

  const d = detail.data;
  const v = d.video;
  const jobActive = d.job?.status === "queued" || d.job?.status === "running";

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-2.5">
        <Link
          to="/videos"
          className="inline-flex items-center gap-1.5 rounded-ctl border border-border-strong bg-surface px-3.5 py-[7px] font-medium hover:bg-surface-2"
        >
          <ArrowLeft size={16} aria-hidden />
          Inspections
        </Link>
        <span className="mono min-w-0 truncate text-text-2">{v.original_filename}</span>
        <span className="chip">{v.process_type}</span>
        {v.disputed && <span className="chip">Disputed</span>}
        <span className="flex-1" />
        {canReanalyze && (
          <Button
            onClick={() => dispute.mutate(!v.disputed)}
            loading={dispute.isPending}
            title="A disputed video's file is never deleted by retention"
          >
            <Flag size={15} aria-hidden />
            {v.disputed ? "Clear dispute" : "Mark disputed"}
          </Button>
        )}
        {canReanalyze && v.stream_url && (
          <Button
            onClick={() => reanalyze.mutate()}
            loading={reanalyze.isPending}
            disabled={jobActive}
          >
            <RefreshCw size={15} aria-hidden />
            Re-analyze
          </Button>
        )}
      </div>

      <InspectionView
        detail={d}
        onReanalyze={canReanalyze ? () => reanalyze.mutate() : undefined}
        reanalyzeBusy={reanalyze.isPending}
        after={<ReviewHistory reviews={d.reviews} />}
      />
    </>
  );
}
