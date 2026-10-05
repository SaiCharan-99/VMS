import { safeNext } from "./nav";

describe("safeNext", () => {
  it.each([
    ["/videos/3?x=1#t", "/videos/3?x=1#t"],
    ["/", "/"],
    [null, "/"],
    ["https://evil.example", "/"],
    ["//evil.example", "/"],
    ["/\\evil.example", "/"],
    ["/\\/evil.example", "/"],
    ["/\tevil", "/"],
    ["javascript:alert(1)", "/"],
  ])("%s -> %s", (input, expected) => {
    expect(safeNext(input)).toBe(expected);
  });
});
