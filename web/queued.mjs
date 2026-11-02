// Queued-state screenshots against the real API: job 1 is started over HTTP so it holds the run lock,
// then job 2 is submitted through the UI and shows "1 job ahead". Finally the job is cancelled from the UI.
import { chromium } from "playwright";
import { readFileSync } from "node:fs";
const csv = process.argv[2];
const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const sizes = { desktop: { width: 1280, height: 800 }, mobile: { width: 390, height: 844 } };
const browser = await chromium.launch();
for (const [name, viewport] of Object.entries(sizes)) {
  const fd = new FormData();
  fd.append("file", new Blob([readFileSync(process.argv[3] ?? csv)], { type: "text/csv" }), "adult500.csv");
  const ds = await (await fetch(`${BASE}/api/datasets`, { method: "POST", body: fd })).json();
  const j1 = await (await fetch(`${BASE}/api/jobs/stage1`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ dataset_id: ds.dataset_id, target: "income", positive_label: ">50K", id_columns: ["fnlwgt"] }) })).json();
  const ctx = await browser.newContext({ viewport });
  const page = await ctx.newPage();
  await page.goto(BASE);
  await page.setInputFiles('input[type="file"]', csv);
  await page.waitForSelector("#target");
  await page.selectOption("#target", "income");
  await page.selectOption("#pos", ">50K");
  const btn = page.locator('button[type="submit"]');
  await btn.dblclick();                                        // double click must create only one job
  await page.getByText(/1 job ahead of yours/).waitFor({ timeout: 20000 }).catch(async (e) => { await page.screenshot({ path: "debug.png" }); throw e; });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `screenshots/2d-queued-${name}.png`, fullPage: true });
  // Back on screen 1 the start button stays disabled while the job is active.
  await page.getByRole("button", { name: /Step 1/ }).click();
  await page.setInputFiles('input[type="file"]', csv);
  await page.waitForSelector("#target");
  await page.selectOption("#target", "income");
  console.log(name, "start disabled while job active:", await btn.isDisabled());
  await page.getByRole("button", { name: /Step 2/ }).click();
  await page.getByRole("button", { name: /Cancel this job/ }).click();
  await page.waitForSelector("text=Clean a table");
  console.log(name, "cancelled, back on screen 1; job1:", j1.job_id.slice(0, 8));
  await ctx.close();
  // let job 1 finish before the next viewport so it is queued behind a fresh running job
  for (;;) { const s = await (await fetch(`${BASE}/api/jobs/${j1.job_id}`)).json(); if (s.status !== "running" && s.status !== "queued") break; await new Promise(r => setTimeout(r, 2000)); }
}
await browser.close();
