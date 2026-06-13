import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("loads Telegram WebApp SDK before the client application", async () => {
  const layout = await readFile(new URL("../src/app/layout.tsx", import.meta.url), "utf8");

  assert.match(layout, /https:\/\/telegram\.org\/js\/telegram-web-app\.js/);
  assert.match(layout, /strategy="beforeInteractive"/);
});
