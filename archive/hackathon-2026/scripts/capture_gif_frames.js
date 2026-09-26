const puppeteer = require("puppeteer-core");
const fs = require("fs");
const path = require("path");

const CACHE_DIR = path.join(process.env.USERPROFILE, ".cache", "puppeteer", "chrome");
function findChrome() {
  const versions = fs.readdirSync(CACHE_DIR);
  const dir = versions[0];
  return path.join(CACHE_DIR, dir, "chrome-win64", "chrome.exe");
}

const OUT_DIR = process.argv[2];
const CYCLE_MS = 8800;
const FRAME_MS = 220; // ~40 frames per cycle

(async () => {
  const browser = await puppeteer.launch({
    executablePath: findChrome(),
    headless: "new",
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 2400, height: 1300 });
  const htmlPath = "file://" + path.resolve("assets/argus-architecture-animated.html");
  await page.goto(htmlPath, { waitUntil: "load" });

  fs.mkdirSync(OUT_DIR, { recursive: true });

  const start = Date.now();
  let frame = 0;
  while (Date.now() - start < CYCLE_MS) {
    const target = start + frame * FRAME_MS;
    const wait = target - Date.now();
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    const file = path.join(OUT_DIR, `frame_${String(frame).padStart(3, "0")}.png`);
    await page.screenshot({ path: file });
    frame++;
  }

  console.log("captured", frame, "frames");
  await browser.close();
})();
