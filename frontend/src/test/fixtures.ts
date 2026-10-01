import type { AnalysisResult } from "@/types/analysis";
import type { Video, VideoDetail } from "@/types/api";

export const video = (over: Partial<Video> = {}): Video => ({
  id: 1,
  uuid: "u1",
  original_filename: "ret_blr01_0931.mp4",
  size_bytes: 1000,
  content_type: "video/mp4",
  process_type: "Return",
  awb: "AWB123456789",
  order_ref: null,
  uploaded_by: 2,
  uploaded_by_name: "Ravi K.",
  station_id: null,
  source: "web",
  duration_s: 42,
  created_at: new Date().toISOString(),
  final_status: "pass",
  stream_url: "/api/v1/videos/1/stream?exp=1&sig=x",
  latest_analysis: {
    id: 9,
    uuid: "a9",
    schema_version: "2.0",
    rubric_id: "return-v1",
    total_score: 88,
    confidence: 0.81,
    status: "pass",
    decision: "Accepted",
    created_at: new Date().toISOString(),
  },
  ...over,
});

export const result: AnalysisResult = {
  schema_version: "2.0",
  process_type: "Return",
  rubric_id: "return-v1",
  engine: { version: "0.2.0", detectors: { ocr: true } },
  video: {
    duration_s: 42,
    fps: 30,
    frames_total: 1260,
    frames_sampled: 127,
    width: 1280,
    height: 720,
  },
  quality: {
    frames_ok: 119,
    frames_blurry: 6,
    frames_dark: 2,
    avg_blur: 88,
    avg_brightness: 120,
    ok_ratio: 0.94,
  },
  barcodes: [{ value: "AWB123456789", symbology: "CODE128", first_seen_s: 3.2, frames_seen: 9 }],
  metrics: { barcode_found: true },
  steps: [
    {
      key: "shipping_label",
      title: "Shipping Label & Barcode",
      weight: 30,
      score: 30,
      status: "met",
      checks: [
        {
          key: "barcode_read",
          passed: true,
          points: 15,
          max_points: 15,
          metric: "barcode_found",
          value: true,
          threshold: true,
        },
      ],
      notes: [],
      evidence: [{ t_s: 3.2, kind: "barcode", image: "evidence/a9/shipping_label_0.jpg" }],
    },
  ],
  total_score: 88,
  confidence: 0.81,
  status: "pass",
  decision: "Accepted",
  caps_applied: [],
  summary: "Accepted after reviewing the return recording.",
  timings_ms: { total: 100 },
};

export const detail = (over: Partial<VideoDetail> = {}): VideoDetail => ({
  video: video(),
  analysis: {
    ...(video().latest_analysis as NonNullable<Video["latest_analysis"]>),
    engine_version: "0.2.0",
    job_id: 5,
    result,
    evidence: [
      {
        id: 31,
        step_key: "shipping_label",
        kind: "barcode",
        t_s: 3.2,
        url: "/api/v1/evidence/31?exp=1&sig=y",
      },
    ],
  },
  reviews: [],
  job: null,
  ...over,
});
