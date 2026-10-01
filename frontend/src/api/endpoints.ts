import { z } from "zod";
import {
  jobSchema,
  pageSchema,
  rubricSchema,
  stationSchema,
  tokenSchema,
  uploadSchema,
  userSchema,
  videoDetailSchema,
  videoSchema,
  type ProcessType,
} from "@/types/api";
import { request, uploadWithProgress } from "./client";

const V1 = "/api/v1";
const videoPage = pageSchema(videoSchema);

export interface VideoQuery {
  status?: string;
  process_type?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

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
  reanalyze: (id: number) => request(`${V1}/videos/${id}/reanalyze`, jobSchema, { method: "POST" }),
  job: (id: number) => request(`${V1}/jobs/${id}`, jobSchema),
  stations: () => request(`${V1}/stations`, z.array(stationSchema)),
  rubrics: () => request(`${V1}/rubrics`, z.array(rubricSchema)),
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
