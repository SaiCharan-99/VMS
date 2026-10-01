import { useQuery } from "@tanstack/react-query";
import { api } from "./endpoints";

export const POLL_MS = 2000;

export function useStations() {
  return useQuery({ queryKey: ["stations"], queryFn: api.stations, staleTime: 5 * 60_000 });
}

export function useRubrics() {
  return useQuery({ queryKey: ["rubrics"], queryFn: api.rubrics, staleTime: Infinity });
}

/** Polls every 2 s while the job is queued or running. */
export function useJob(jobId: number | undefined) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.job(jobId as number),
    enabled: jobId !== undefined,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "done" || s === "failed" ? false : POLL_MS;
    },
  });
}

export function useVideo(id: number | undefined) {
  return useQuery({
    queryKey: ["video", id],
    queryFn: () => api.video(id as number),
    enabled: id !== undefined,
    // Keep polling while an analysis is pending so the page updates on its own.
    refetchInterval: (q) => {
      const job = q.state.data?.job;
      return job && (job.status === "queued" || job.status === "running") ? POLL_MS : false;
    },
  });
}
