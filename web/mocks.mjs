// Screenshots of API states that are hard to reach for real (mid-run progress, planner unavailable).
// The job endpoints are mocked at the network layer; the dataset upload hits the real API.
import { chromium } from "playwright";
const csv = process.argv[2];
const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const sizes = { desktop: { width: 1280, height: 800 }, mobile: { width: 390, height: 844 } };
const base = { job_id: "mock", planner: "groq", message: null, warnings: [], can_rerun_with_rule: false, stage2: { suggested: false, approved: false } };
const browser = await chromium.launch();
for (const [name, viewport] of Object.entries(sizes)) {
  for (const [tag, job] of [
    ["2a-progress", { ...base, planner: "rule", status: "running", progress: { iteration: 7, of: 16 } }],
    ["2c-planner-unavailable", { ...base, status: "planner_unavailable", progress: { iteration: 0, of: 16 }, can_rerun_with_rule: true,
      message: "Groq planner unavailable (APIConnectionError: Connection error.). Rerun with the rule planner." }],
  ]) {
    const ctx = await browser.newContext({ viewport });
    const page = await ctx.newPage();
    await page.route("**/api/jobs/stage1", (r) => r.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify({ job_id: "mock", status: "queued", planner: "groq", warnings: [] }) }));
    await page.route("**/api/jobs/mock", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(job) }));
    await page.goto(BASE);
    await page.setInputFiles('input[type="file"]', csv);
    await page.waitForSelector("#target");
    await page.selectOption("#target", "income");
    await page.click('button[type="submit"]');
    await page.waitForSelector(".progress");
    await page.waitForTimeout(600);
    await page.screenshot({ path: `screenshots/${tag}-${name}.png`, fullPage: true });
    await ctx.close();
  }
}
await browser.close();
