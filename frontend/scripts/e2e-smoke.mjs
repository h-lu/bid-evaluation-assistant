import { chromium } from "playwright";

const baseUrl = process.env.E2E_BASE_URL || "http://127.0.0.1:5173";

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto(`${baseUrl}/dashboard`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("h1");
  const title = await page.textContent("h1");
  if (!title || !title.includes("Bid Evaluation Assistant")) {
    throw new Error(`Unexpected title: ${title}`);
  }
  await page.waitForSelector("nav.menu");
  await page.goto(`${baseUrl}/evaluations`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("h2");

  await browser.close();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
