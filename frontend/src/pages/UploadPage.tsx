import { UploadCloud } from "lucide-react";
import { useEffect, useReducer, useRef, useState, type DragEvent } from "react";
import { api } from "@/api/endpoints";
import { useStations } from "@/api/queries";
import { UploadQueue } from "@/components/UploadQueue";
import { Button, Card, CardBody, CardHeader, Segmented, useToast } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { ProcessType } from "@/types/api";
import { ACCEPTED_TYPES, isVideoFile, nextToStart, queueReducer } from "@/upload/queue";

const MAX_MB = 500;
let seq = 0;

export function UploadPage() {
  const [items, dispatch] = useReducer(queueReducer, []);
  const [processType, setProcessType] = useState<ProcessType>("Forward");
  const [stationId, setStationId] = useState("");
  const [awb, setAwb] = useState("");
  const [orderRef, setOrderRef] = useState("");
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const stations = useStations();
  const toast = useToast();

  // Start queued uploads while fewer than 2 are running.
  useEffect(() => {
    for (const item of nextToStart(items)) {
      dispatch({ type: "start", id: item.id });
      const handle = api.upload(item.file, item.settings, (p) =>
        dispatch({ type: "progress", id: item.id, progress: p }),
      );
      handle.promise
        .then((res) =>
          dispatch({
            type: "uploaded",
            id: item.id,
            videoId: res.video.id,
            jobId: res.job?.id,
            duplicate: res.duplicate,
          }),
        )
        .catch((err: unknown) =>
          dispatch({
            type: "error",
            id: item.id,
            error: err instanceof Error ? err.message : "Upload failed.",
          }),
        );
    }
  }, [items]);

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    const all = Array.from(list);
    const files = all.filter(isVideoFile);
    const skipped = all.length - files.length;
    if (skipped) toast(`${skipped} file(s) skipped: not a video.`, "error");
    const tooBig = files.filter((f) => f.size > MAX_MB * 1024 * 1024);
    if (tooBig.length) toast(`${tooBig.length} file(s) over ${MAX_MB} MB skipped.`, "error");
    const ok = files.filter((f) => f.size <= MAX_MB * 1024 * 1024);
    if (!ok.length) return;
    dispatch({
      type: "add",
      files: ok,
      ids: ok.map(() => `u${++seq}`),
      settings: {
        process_type: processType,
        awb: awb.trim() || undefined,
        order_ref: orderRef.trim() || undefined,
        station_id: stationId ? Number(stationId) : undefined,
      },
    });
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  return (
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
      <div className="grid min-w-0 gap-4">
        <section
          aria-label="Drop zone"
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            "rounded-card border-[1.5px] border-dashed bg-surface px-6 py-11 text-center",
            dragging ? "border-accent bg-accent-soft" : "border-border-strong",
          )}
        >
          <div className="mx-auto mb-3 grid h-11 w-11 place-items-center rounded-card bg-accent-soft text-accent">
            <UploadCloud size={22} strokeWidth={2} aria-hidden />
          </div>
          <div className="font-semibold">Drop inspection videos here</div>
          <div className="mb-3.5 mt-1 text-sm text-text-2">
            MP4, MOV, AVI or MKV · up to {MAX_MB} MB each
          </div>
          <Button onClick={() => inputRef.current?.click()}>Browse files</Button>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED_TYPES}
            className="sr-only"
            tabIndex={-1}
            aria-label="Choose video files"
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </section>

        {items.length > 0 && (
          <Card>
            <CardHeader
              title="This batch"
              actions={
                <span className="text-xs text-text-3">
                  {items.length} file{items.length === 1 ? "" : "s"}
                </span>
              }
            />
            <UploadQueue items={items} onRemove={(id) => dispatch({ type: "remove", id })} />
          </Card>
        )}
      </div>

      <Card>
        <CardBody className="grid gap-3.5">
          <div className="grid gap-1.5">
            <span id="pt-label" className="text-[12.5px] font-medium text-text-2">
              Process type
            </span>
            <Segmented
              label="Process type"
              stretch
              value={processType}
              onChange={setProcessType}
              options={[
                { value: "Forward", label: "Forward" },
                { value: "Return", label: "Return" },
              ]}
            />
          </div>
          <div className="grid gap-1.5">
            <label htmlFor="station" className="text-[12.5px] font-medium text-text-2">
              Station
            </label>
            <select
              id="station"
              className="select"
              value={stationId}
              onChange={(e) => setStationId(e.target.value)}
            >
              <option value="">No station</option>
              {stations.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} · {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-1.5">
            <label htmlFor="awb" className="text-[12.5px] font-medium text-text-2">
              AWB (optional)
            </label>
            <input
              id="awb"
              className="input mono"
              placeholder="Auto-detected from barcode"
              value={awb}
              onChange={(e) => setAwb(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <label htmlFor="order" className="text-[12.5px] font-medium text-text-2">
              Order ref (optional)
            </label>
            <input
              id="order"
              className="input mono"
              value={orderRef}
              onChange={(e) => setOrderRef(e.target.value)}
            />
          </div>
          <p className="m-0 text-xs text-text-3">These settings apply to the files you add next.</p>
          <div className="rounded-ctl bg-surface-2 px-3 py-2.5 text-[12.5px] text-text-2">
            <b className="text-text">Tips for a passing video</b>
            <br />
            Record at 720p, not 1080p. Hold the label still for 2 seconds. Show all 6 sides before
            you open the parcel.
            <br />
            <b className="mt-2 inline-block text-text">Large files?</b>
            <br />
            Phone: the Video Compress app. PC: HandBrake, RF 28.
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
