import { z } from "zod";
import {
  apiKeyCreatedSchema,
  apiKeySchema,
  auditEntrySchema,
  reportSummarySchema,
  reviewSchema,
  warehouseSchema,
  jobSchema,
  pageSchema,
  rubricSchema,
  stationSchema,
  tokenSchema,
  uploadSchema,
  userSchema,
  videoDetailSchema,
  videoSchema,
  type GroupBy,
  type ProcessType,
  type ReasonCode,
  type Role,
} from "@/types/api";
import { downloadFile, request, uploadWithProgress } from "./client";

const V1 = "/api/v1";
const videoPage = pageSchema(videoSchema);

export interface VideoQuery {
  status?: string;
  station_id?: number | string;
  process_type?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface ReportQuery {
  date_from: string;
  date_to: string;
  group_by?: GroupBy;
  process_type?: string;
  station_id?: number | string;
}

export interface AuditQuery {
  action?: string;
  entity_type?: string;
  entity_id?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface UserInput {
  email: string;
  name: string;
  password: string;
  role: Role;
  warehouse_id?: number | null;
}

export type UserPatch = Partial<Pick<UserInput, "name" | "role" | "password" | "warehouse_id">> & {
  is_active?: boolean;
};

/** Minutes east of UTC, so the API buckets days the way the user sees them. */
export const tzOffsetMin = () => -new Date().getTimezoneOffset();

const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});

function qs(params: object): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  login: (email: string, password: string) =>
    request(`${V1}/auth/login`, tokenSchema, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request(`${V1}/auth/me`, userSchema),
  videos: (q: VideoQuery) => request(`${V1}/videos${qs(q)}`, videoPage),
  video: (id: number) => request(`${V1}/videos/${id}`, videoDetailSchema),
  setDisputed: (id: number, disputed: boolean) =>
    request(`${V1}/videos/${id}/dispute`, videoSchema, {
      method: "PUT",
      body: JSON.stringify({ disputed }),
    }),
  reanalyze: (id: number) => request(`${V1}/videos/${id}/reanalyze`, jobSchema, { method: "POST" }),
  job: (id: number) => request(`${V1}/jobs/${id}`, jobSchema),
  stations: () => request(`${V1}/stations`, z.array(stationSchema)),
  rubrics: () => request(`${V1}/rubrics`, z.array(rubricSchema)),
  reviewQueue: (q: { process_type?: string; station_id?: number | string; page_size?: number }) =>
    request(`${V1}/review-queue${qs(q)}`, videoPage),
  review: (
    id: number,
    body: { final_status: "pass" | "fail"; reason_code: ReasonCode; comment?: string },
  ) => request(`${V1}/videos/${id}/reviews`, reviewSchema, json("POST", body)),
  reportSummary: (q: ReportQuery) =>
    request(
      `${V1}/reports/summary${qs({ ...q, tz_offset_min: tzOffsetMin() })}`,
      reportSummarySchema,
    ),
  exportCsv: (q: VideoQuery) =>
    downloadFile(
      `${V1}/reports/export.csv${qs({ ...q, tz_offset_min: tzOffsetMin() })}`,
      "vms-export.csv",
    ),
  admin: {
    users: () => request(`${V1}/admin/users?page_size=200`, pageSchema(userSchema)),
    createUser: (body: UserInput) => request(`${V1}/admin/users`, userSchema, json("POST", body)),
    updateUser: (id: number, body: UserPatch) =>
      request(`${V1}/admin/users/${id}`, userSchema, json("PATCH", body)),
    warehouses: () => request(`${V1}/admin/warehouses`, z.array(warehouseSchema)),
    createWarehouse: (body: { code: string; name: string }) =>
      request(`${V1}/admin/warehouses`, warehouseSchema, json("POST", body)),
    createStation: (body: { warehouse_id: number; code: string; name: string }) =>
      request(`${V1}/admin/stations`, stationSchema, json("POST", body)),
    apiKeys: () => request(`${V1}/admin/api-keys`, z.array(apiKeySchema)),
    createApiKey: (name: string) =>
      request(`${V1}/admin/api-keys`, apiKeyCreatedSchema, json("POST", { name })),
    revokeApiKey: (id: number) => request(`${V1}/admin/api-keys/${id}`, null, { method: "DELETE" }),
    auditLog: (q: AuditQuery) =>
      request(`${V1}/admin/audit-log${qs(q)}`, pageSchema(auditEntrySchema)),
  },
  upload: (
    file: File,
    fields: { process_type: ProcessType; awb?: string; order_ref?: string; station_id?: number },
    onProgress: (f: number) => void,
  ) => {
    const form = new FormData();
    form.append("file", file);
    for (const [k, v] of Object.entries(fields))
      if (v !== undefined && v !== "") form.append(k, String(v));
    return uploadWithProgress(`${V1}/videos`, form, uploadSchema, onProgress);
  },
};
