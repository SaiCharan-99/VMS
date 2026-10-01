// Mirrors backend/vms/api/schemas.py (IMPLEMENTATION.md §8).
import { z } from "zod";
import { analysisResultSchema, statusSchema } from "./analysis";

export const roleSchema = z.enum(["operator", "reviewer", "admin"]);
export const processTypeSchema = z.enum(["Forward", "Return"]);
export const finalStatusSchema = z.enum(["pending", "pass", "review", "fail"]);
export const jobStatusSchema = z.enum(["queued", "running", "done", "failed"]);

export const userSchema = z.object({
  id: z.number(),
  email: z.string(),
  name: z.string(),
  role: roleSchema,
  warehouse_id: z.number().nullable(),
  is_active: z.boolean(),
  created_at: z.string(),
  last_login_at: z.string().nullable(),
});

export const tokenSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  expires_in: z.number(),
  user: userSchema,
});

export const jobSchema = z.object({
  id: z.number(),
  video_id: z.number(),
  status: jobStatusSchema,
  progress: z.number(),
  attempts: z.number(),
  max_attempts: z.number(),
  error: z.string().nullable(),
  created_at: z.string(),
  started_at: z.string().nullable(),
  finished_at: z.string().nullable(),
});

export const analysisBriefSchema = z.object({
  id: z.number(),
  uuid: z.string(),
  schema_version: z.string(),
  rubric_id: z.string(),
  total_score: z.number(),
  confidence: z.number(),
  status: z.string(),
  decision: z.string(),
  created_at: z.string(),
});

export const evidenceSchema = z.object({
  id: z.number(),
  step_key: z.string(),
  kind: z.string(),
  t_s: z.number(),
  url: z.string(),
});

export const analysisSchema = analysisBriefSchema.extend({
  engine_version: z.string(),
  job_id: z.number().nullable(),
  // Legacy imports keep their schema 1.0 dict; the UI shows a reduced view for those.
  result: z.union([analysisResultSchema, z.record(z.unknown())]),
  evidence: z.array(evidenceSchema),
});

export const videoSchema = z.object({
  id: z.number(),
  uuid: z.string(),
  original_filename: z.string(),
  size_bytes: z.number().nullable(),
  content_type: z.string().nullable(),
  process_type: processTypeSchema,
  awb: z.string().nullable(),
  order_ref: z.string().nullable(),
  uploaded_by: z.number().nullable(),
  uploaded_by_name: z.string().nullable().optional(),
  station_id: z.number().nullable(),
  source: z.enum(["web", "api", "legacy"]),
  duration_s: z.number().nullable(),
  created_at: z.string(),
  final_status: finalStatusSchema,
  stream_url: z.string().nullable().optional(),
  latest_analysis: analysisBriefSchema.nullable().optional(),
  human_reviewed: z.boolean().optional(),
});

export const reviewSchema = z.object({
  id: z.number(),
  analysis_id: z.number(),
  reviewer_id: z.number(),
  reviewer_name: z.string().nullable().optional(),
  final_status: statusSchema.exclude(["review"]),
  reason_code: z.string(),
  comment: z.string().nullable(),
  created_at: z.string(),
});

export const videoDetailSchema = z.object({
  video: videoSchema,
  analysis: analysisSchema.nullable(),
  reviews: z.array(reviewSchema),
  job: jobSchema.nullable(),
});

export const uploadSchema = z.object({
  video: videoSchema,
  job: jobSchema.nullable(),
  duplicate: z.boolean(),
});

export const pageSchema = <T extends z.ZodTypeAny>(item: T) =>
  z.object({ items: z.array(item), total: z.number(), page: z.number(), page_size: z.number() });

export const stationSchema = z.object({
  id: z.number(),
  warehouse_id: z.number(),
  code: z.string(),
  name: z.string(),
});

export const rubricSchema = z.object({
  id: z.string(),
  process_type: processTypeSchema,
  title: z.string(),
  steps: z.array(
    z.object({ key: z.string(), title: z.string(), description: z.string(), weight: z.number() }),
  ),
});

export const REASON_CODES = [
  "label_unclear",
  "seal_not_shown",
  "tags_not_shown",
  "product_not_inspected",
  "video_quality",
  "false_negative_model",
  "other",
] as const;
export type ReasonCode = (typeof REASON_CODES)[number];

const statusCounts = {
  total: z.number(),
  pass: z.number(),
  review: z.number(),
  fail: z.number(),
  pending: z.number(),
};

export const reportGroupSchema = z.object({
  ...statusCounts,
  key: z.string(),
  label: z.string(),
  pass_rate: z.number().nullable(),
  avg_score: z.number().nullable(),
});

export const failedCheckSchema = z.object({
  process_type: processTypeSchema,
  step_key: z.string(),
  check_key: z.string(),
  step_title: z.string(),
  note: z.string().nullable(),
  failures: z.number(),
  evaluated: z.number(),
  rate: z.number().nullable(),
});

export const reportSummarySchema = z.object({
  date_from: z.string(),
  date_to: z.string(),
  group_by: z.enum(["day", "station", "operator", "process_type"]),
  totals: z.object(statusCounts),
  analyzed: z.number(),
  pass_rate: z.number().nullable(),
  review_rate: z.number().nullable(),
  reviewed: z.number(),
  agreement_rate: z.number().nullable(),
  agreement_n: z.number(),
  avg_score: z.number().nullable(),
  avg_turnaround_s: z.number().nullable(),
  top_failed_checks: z.array(failedCheckSchema),
  groups: z.array(reportGroupSchema),
});

export const warehouseSchema = z.object({
  id: z.number(),
  code: z.string(),
  name: z.string(),
  created_at: z.string(),
});

export const apiKeySchema = z.object({
  id: z.number(),
  name: z.string(),
  created_by: z.number(),
  created_at: z.string(),
  revoked_at: z.string().nullable(),
});

export const apiKeyCreatedSchema = apiKeySchema.extend({ key: z.string() });

export const auditEntrySchema = z.object({
  id: z.number(),
  actor_user_id: z.number().nullable(),
  actor_api_key_id: z.number().nullable(),
  action: z.string(),
  entity_type: z.string(),
  entity_id: z.string().nullable(),
  data: z.record(z.unknown()).nullable(),
  created_at: z.string(),
});

export type Review = z.infer<typeof reviewSchema>;
export type ReportSummary = z.infer<typeof reportSummarySchema>;
export type ReportGroup = z.infer<typeof reportGroupSchema>;
export type FailedCheck = z.infer<typeof failedCheckSchema>;
export type GroupBy = ReportSummary["group_by"];
export type Warehouse = z.infer<typeof warehouseSchema>;
export type ApiKey = z.infer<typeof apiKeySchema>;
export type ApiKeyCreated = z.infer<typeof apiKeyCreatedSchema>;
export type AuditEntry = z.infer<typeof auditEntrySchema>;
export type Role = z.infer<typeof roleSchema>;
export type ProcessType = z.infer<typeof processTypeSchema>;
export type FinalStatus = z.infer<typeof finalStatusSchema>;
export type User = z.infer<typeof userSchema>;
export type Token = z.infer<typeof tokenSchema>;
export type Job = z.infer<typeof jobSchema>;
export type Video = z.infer<typeof videoSchema>;
export type VideoDetail = z.infer<typeof videoDetailSchema>;
export type Evidence = z.infer<typeof evidenceSchema>;
export type Upload = z.infer<typeof uploadSchema>;
export type Station = z.infer<typeof stationSchema>;
export type Rubric = z.infer<typeof rubricSchema>;
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };
