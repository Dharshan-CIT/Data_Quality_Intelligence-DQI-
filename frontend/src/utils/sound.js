/** Tiny synthesized UI sounds via Web Audio — no audio files to ship or load. */

let ctx = null;
function getCtx() {
  if (!ctx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;
    ctx = new AudioCtx();
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

function tone({ freq, duration, type = 'sine', gain = 0.06, glideTo = null }) {
  const audioCtx = getCtx();
  if (!audioCtx) return;
  const osc = audioCtx.createOscillator();
  const amp = audioCtx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
  if (glideTo) osc.frequency.exponentialRampToValueAtTime(glideTo, audioCtx.currentTime + duration);
  amp.gain.setValueAtTime(gain, audioCtx.currentTime);
  amp.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
  osc.connect(amp);
  amp.connect(audioCtx.destination);
  osc.start();
  osc.stop(audioCtx.currentTime + duration);
}

/** Soft, short mechanical "tap" — for buttons, chips, tabs. */
export function playClick() {
  tone({ freq: 1000, duration: 0.045, type: 'square', gain: 0.035, glideTo: 700 });
}

/** A touch brighter — for primary/affirmative actions (Apply, Commit, Recompute). */
export function playConfirm() {
  tone({ freq: 740, duration: 0.07, type: 'sine', gain: 0.05, glideTo: 1180 });
}

/** Low, short — for toggles/switches (dark mode, filter chips off). */
export function playToggle() {
  tone({ freq: 500, duration: 0.03, type: 'square', gain: 0.03 });
}

let soundEnabled = true;
try {
  soundEnabled = localStorage.getItem('dqi_sound') !== '0';
} catch { /* localStorage unavailable — default to on */ }

export function isSoundEnabled() {
  return soundEnabled;
}

export function setSoundEnabled(value) {
  soundEnabled = value;
  try { localStorage.setItem('dqi_sound', value ? '1' : '0'); } catch { /* ignore */ }
}

function guarded(fn) {
  return (...args) => { if (soundEnabled) fn(...args); };
}

export const click = guarded(playClick);
export const confirm = guarded(playConfirm);
export const toggle = guarded(playToggle);
