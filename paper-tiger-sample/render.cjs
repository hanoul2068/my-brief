// Renders scene.html frame by frame in headless Chromium, synthesizes a tiny soundtrack, muxes MP4 with ffmpeg.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const dir = __dirname;
const out = path.join(dir, 'paper-tiger-sample.mp4');
const wav = path.join(dir, 'music.wav');

function writeMusic(seconds) {
  // soft kalimba-ish plucks on a pentatonic scale
  const sr = 44100, n = Math.floor(sr * seconds), buf = new Float32Array(n);
  const notes = [0, 3, 5, 7, 10, 12, 10, 7, 5, 7, 12, 15];
  const beat = 0.375;
  notes.forEach((semi, i) => {
    const f = 293.66 * Math.pow(2, semi / 12), start = Math.floor(i * beat * sr);
    for (let k = 0; k < sr * 1.6 && start + k < n; k++) {
      const tt = k / sr, env = Math.exp(-tt * 3.2) * Math.min(1, tt * 200);
      buf[start + k] += 0.22 * env * (Math.sin(2 * Math.PI * f * tt) + 0.3 * Math.sin(2 * Math.PI * f * 2.01 * tt) * Math.exp(-tt * 6));
    }
  });
  // low pad
  for (let k = 0; k < n; k++) { const tt = k / sr, fade = Math.min(1, tt / 1, (seconds - tt) / 1);
    buf[k] += 0.05 * fade * (Math.sin(2 * Math.PI * 146.83 * tt) + Math.sin(2 * Math.PI * 220 * tt)); }
  const data = Buffer.alloc(44 + n * 2);
  data.write('RIFF', 0); data.writeUInt32LE(36 + n * 2, 4); data.write('WAVEfmt ', 8);
  data.writeUInt32LE(16, 16); data.writeUInt16LE(1, 20); data.writeUInt16LE(1, 22);
  data.writeUInt32LE(sr, 24); data.writeUInt32LE(sr * 2, 28); data.writeUInt16LE(2, 32); data.writeUInt16LE(16, 34);
  data.write('data', 36); data.writeUInt32LE(n * 2, 40);
  for (let k = 0; k < n; k++) data.writeInt16LE(Math.max(-1, Math.min(1, buf[k])) * 32000 | 0, 44 + k * 2);
  fs.writeFileSync(wav, data);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.join(dir, 'scene.html') + '?render');
  const { FPS, DURATION } = await page.evaluate(() => ({ FPS: window.FPS, DURATION: window.DURATION }));
  writeMusic(DURATION);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-i', wav, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-c:a', 'aac', '-shortest', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const canvas = await page.$('canvas');
  const total = FPS * DURATION;
  for (let i = 0; i < total; i++) {
    await page.evaluate(t => window.renderFrame(t), i / FPS);
    const png = await canvas.screenshot({ type: 'png' });
    if (i === Math.floor(total * 0.85)) fs.writeFileSync(path.join(dir, 'still.png'), png);
    ff.stdin.write(png);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  fs.unlinkSync(wav);
  console.log('done', out);
})();
