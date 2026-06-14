import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("constraint editor saves independently from the request form", async () => {
  const source = await readFile(new URL("../src/app/page.tsx", import.meta.url), "utf8");

  assert.match(source, /async function handleSaveConstraints\(\)/);
  assert.match(source, /onClick=\{handleSaveConstraints\}/);
  assert.doesNotMatch(source, /form="request-form"[\s\S]{0,80}Сохранить параметры/);
  assert.match(source, /disabled=\{editMode === "constraints"\}/);
});
