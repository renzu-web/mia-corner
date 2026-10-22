// screenshot every page of mia's corner. run from /workspace/mia-site:
//   NODE_PATH=/workspace/pausia/node_modules node tools/shots.js
const puppeteer = require("puppeteer");
const fs = require("fs");
const path = require("path");

const CHROME = process.env.HOME + "/.local/chs/chrome-headless-shell-linux64/chrome-headless-shell";
const BASE = "http://127.0.0.1:8099/";
const OUT = path.join(__dirname, "..", "shots");

const PAGES = [
  ["index", "index.html"],
  ["diary", "diary.html"],
  ["coffee", "coffee.html"],
  ["looks", "looks.html"],
  ["lab", "lab.html"],
  ["404", "404.html"],
];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "shell",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--font-render-hinting=none"],
  });

  for (const [name, file] of PAGES) {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
    await page.goto(BASE + file, { waitUntil: "networkidle2", timeout: 45000 });
    await new Promise((r) => setTimeout(r, 700));
    const h = await page.evaluate(() => document.body.scrollHeight);
    await page.screenshot({ path: path.join(OUT, name + ".png"), fullPage: true });
    console.log(`${name}.png  ${h}px tall`);
    await page.close();
  }

  // one phone view of the front page, because that is where it will be read
  const m = await browser.newPage();
  await m.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true });
  await m.goto(BASE + "index.html", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 700));
  await m.screenshot({ path: path.join(OUT, "index-mobile.png"), fullPage: true });
  console.log("index-mobile.png");

  await browser.close();

  // dark mode, because i built for it and should check it
  const browser2 = await puppeteer.launch({
    executablePath: CHROME,
    headless: "shell",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--font-render-hinting=none"],
  });
  const d = await browser2.newPage();
  await d.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "dark" }]);
  await d.setViewport({ width: 1280, height: 900 });
  await d.goto(BASE + "index.html", { waitUntil: "networkidle2" });
  await new Promise((r) => setTimeout(r, 700));
  await d.screenshot({ path: path.join(OUT, "index-dark.png"), fullPage: true });
  console.log("index-dark.png");
  await browser2.close();
})().catch((e) => {
  console.error("FAILED:", e.message);
  process.exit(1);
});
