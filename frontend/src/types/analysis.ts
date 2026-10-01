// Mirrors backend/vms/analysis/result.py — IMPLEMENTATION.md §5 (schema_version "2.0").
// Keep in sync by hand; bump together with the backend contract.
import { z } from "zod";

export const SCHEMA_VERSION = "2.0";

export const statusSchema = z.enum(["pass", "review", "fail"]);
export const stepStatusSchema = z.enum(["met", "partial", "missed"]);
const metricValue = z.union([z.number(), z.boolean()]);

export const checkSchema = z.object({
  key: z.string(),
  passed: z.boolean(),
  points: z.number(),
  max_points: z.number(),
  metric: z.string(),
  value: metricValue.nullable(),
  threshold: metricValue,
  note: z.string().nullable().optional(),
});

export const evidenceRefSchema = z.object({
  t_s: z.number(),
  kind: z.string(),
  image: z.string().nullable().optional(),
});

export const stepSchema = z.object({
  key: z.string(),
  title: z.string(),
  weight: z.number(),
  score: z.number(),
  status: stepStatusSchema,
  checks: z.array(checkSchema),
  notes: z.array(z.string()).default([]),
  evidence: z.array(evidenceRefSchema).default([]),
});

export const barcodeSchema = z.object({
  value: z.string(),
  symbology: z.string(),
  first_seen_s: z.number(),
  frames_seen: z.number(),
});

export const analysisResultSchema = z.object({
  schema_version: z.literal(SCHEMA_VERSION),
  process_type: z.enum(["Forward", "Return"]),
  rubric_id: z.string(),
  engine: z.object({
    version: z.string(),
    detectors: z.record(z.union([z.boolean(), z.string()])),
  }),
  video: z.object({
    duration_s: z.number(),
    fps: z.number(),
    frames_total: z.number(),
    frames_sampled: z.number(),
    width: z.number(),
    height: z.number(),
  }),
  quality: z.object({
    frames_ok: z.number(),
    frames_blurry: z.number(),
    frames_dark: z.number(),
    avg_blur: z.number(),
    avg_brightness: z.number(),
    ok_ratio: z.number(),
  }),
  barcodes: z.array(barcodeSchema),
  metrics: z.record(metricValue),
  steps: z.array(stepSchema),
  total_score: z.number(),
  confidence: z.number(),
  status: statusSchema,
  decision: z.string(),
  caps_applied: z.array(z.string()),
  summary: z.string(),
  timings_ms: z.record(z.number()),
});

export type Status = z.infer<typeof statusSchema>;
export type StepStatus = z.infer<typeof stepStatusSchema>;
export type Check = z.infer<typeof checkSchema>;
export type Step = z.infer<typeof stepSchema>;
export type Barcode = z.infer<typeof barcodeSchema>;
export type AnalysisResult = z.infer<typeof analysisResultSchema>;
