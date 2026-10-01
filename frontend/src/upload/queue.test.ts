import { nextToStart, queueReducer, type UploadItem } from "./queue";

const file = (name: string) => new File(["x"], name, { type: "video/mp4" });
const settings = { process_type: "Forward" as const };

function add(n: number): UploadItem[] {
  const files = Array.from({ length: n }, (_, i) => file(`v${i}.mp4`));
  return queueReducer([], { type: "add", files, settings, ids: files.map((_, i) => `u${i}`) });
}

describe("upload queue reducer", () => {
  it("adds files as queued", () => {
    const s = add(3);
    expect(s.map((i) => [i.id, i.phase, i.progress])).toEqual([
      ["u0", "queued", 0],
      ["u1", "queued", 0],
      ["u2", "queued", 0],
    ]);
  });

  it("starts at most 2 uploads at a time", () => {
    let s = add(3);
    expect(nextToStart(s).map((i) => i.id)).toEqual(["u0", "u1"]);
    s = queueReducer(s, { type: "start", id: "u0" });
    s = queueReducer(s, { type: "start", id: "u1" });
    expect(nextToStart(s)).toEqual([]);
    s = queueReducer(s, { type: "uploaded", id: "u0", videoId: 7, jobId: 3, duplicate: false });
    expect(nextToStart(s).map((i) => i.id)).toEqual(["u2"]);
  });

  it("tracks progress, clamped to 0..1, then the uploaded ids", () => {
    let s = queueReducer(add(1), { type: "start", id: "u0" });
    s = queueReducer(s, { type: "progress", id: "u0", progress: 1.7 });
    expect(s[0]?.progress).toBe(1);
    s = queueReducer(s, { type: "uploaded", id: "u0", videoId: 7, jobId: 3, duplicate: true });
    expect(s[0]).toMatchObject({ phase: "uploaded", videoId: 7, jobId: 3, duplicate: true });
  });

  it("records errors and only removes items that are not uploading", () => {
    let s = queueReducer(add(2), { type: "start", id: "u0" });
    s = queueReducer(s, { type: "error", id: "u1", error: "Too big" });
    expect(s[1]).toMatchObject({ phase: "error", error: "Too big" });
    s = queueReducer(s, { type: "remove", id: "u0" });
    s = queueReducer(s, { type: "remove", id: "u1" });
    expect(s.map((i) => i.id)).toEqual(["u0"]);
  });
});
