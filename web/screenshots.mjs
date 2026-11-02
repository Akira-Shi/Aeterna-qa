// Drives the real app against the real API and saves screenshots to web/screenshots/.
// Usage: node screenshots.mjs <path-to-csv> [screens, e.g. 1,2,3]   (API on :8000, dev server on :5173)
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const csv = process.argv[2];
const want = (process.argv[3] ?? "1,2,3").split(",");
const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const sizes = { desktop: { width: 1280, height: 800 }, mobile: { width: 390, height: 844 } };
mkdirSync("screenshots", { recursive: true });

const browser = await chromium.launch();
for (const [name, viewport] of Object.entries(sizes)) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const shot = (n, full = true) => page.screenshot({ path: `screenshots/${n}-${name}.png`, fullPage: full });
  await page.goto(BASE);
  await page.setInputFiles('input[type="file"]', csv);
  await page.waitForSelector("#target");

  if (want.includes("1")) {
    await shot("1a-upload-empty");
    // Inline validation error: a numeric column is not a usable two-class target here.
    await page.selectOption("#target", "age");
    await page.selectOption("#task", "binary");
    await page.click('button[type="submit"]');
    await page.waitForSelector(".alert");
    await shot("1b-upload-error");
  }
  await page.selectOption("#target", "income");
  await page.selectOption("#pos", ">50K");
  await page.locator("details.opt summary").click();
  await page.locator(".chip", { hasText: /^fnlwgt$/ }).first().click();
  if (want.includes("1")) await shot("1c-upload-ready");
  await page.locator("details.opt summary").click();
  await page.click('button[type="submit"]');

  if (!want.includes("2") && !want.includes("3")) { await ctx.close(); continue; }
  await page.waitForSelector("ul.repairs", { timeout: 300000 });
  if (want.includes("2")) {
    await page.waitForTimeout(800);
    await shot("2b-repairs");
  }

  if (want.includes("3")) {
    await page.getByRole("button", { name: /Continue to pipeline/ }).click();
    await page.waitForSelector(".step-card", { timeout: 300000 });
    await page.waitForTimeout(500);
    await shot("3a-suggest");
    await page.getByRole("button", { name: /Approve/ }).click();
    await page.waitForSelector("table.preview", { timeout: 300000 });
    await page.waitForTimeout(500);
    await shot("3b-download");
  }
  await ctx.close();
}
await browser.close();
