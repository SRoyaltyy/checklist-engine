// Venice wake - watches for a WAKE.json flag and submits the prompt itself.
// Install in Tampermonkey or Violentmonkey. Keep this chat open in a tab.
// It polls: this is not a push. A server cannot reach the chat, a script in the page can.
// One wake per flag id, remembered in localStorage so a reload does not re-fire.
// The badge in the bottom right corner pauses and resumes it.

// ==UserScript==
// @name         Venice wake
// @version      1.1
// @match        https://venice.ai/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  "use strict";
  const BRANCH = "venice/calendar-announce-ledger";
  const RAW = `https://raw.githubusercontent.com/SRoyaltyy/checklist-engine/${BRANCH}/agent/WAKE.json`;
  const POLL_MS = 30000;
  const COOLDOWN_MS = 4 * 60000;
  const KEY_LAST_ID = "veniceWakeLastId";
  const KEY_LAST_FIRE = "veniceWakeLastFire";
  const KEY_PAUSE = "veniceWakePaused";

  const paused = () => localStorage.getItem(KEY_PAUSE) === "1";

  function badge() {
    const el = document.createElement("div");
    Object.assign(el.style, {
      position: "fixed", right: "12px", bottom: "12px", zIndex: 999999,
      font: "12px system-ui, sans-serif", padding: "6px 10px", borderRadius: "8px",
      cursor: "pointer", color: "#fff", userSelect: "none", opacity: "0.9",
    });
    const paint = () => {
      el.textContent = "wake " + (paused() ? "PAUSED" : "on");
      el.style.background = paused() ? "#a33" : "#2a7";
    };
    el.addEventListener("click", () => {
      localStorage.setItem(KEY_PAUSE, paused() ? "0" : "1");
      paint();
    });
    paint();
    document.body.appendChild(el);
  }

  function composer() {
    const pick = (sel) => document.querySelector(sel);
    return (
      pick('textarea[placeholder*="Ask" i]') ||
      pick('[contenteditable="true"][data-placeholder*="Ask" i]') ||
      pick('[contenteditable="true"][aria-label*="Ask" i]') ||
      pick("textarea") ||
      [...document.querySelectorAll('[contenteditable="true"]')].pop()
    );
  }

  function busy() {
    return [...document.querySelectorAll("button")].some((b) =>
      /stop|cancel/i.test(b.getAttribute("aria-label") || b.title || ""));
  }

  function hasDraft(box) {
    if (!box) return false;
    const text = box.tagName === "TEXTAREA" ? box.value : box.textContent;
    return (text || "").trim().length > 0;
  }

  function type(box, text) {
    if (box.tagName === "TEXTAREA") {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
      setter.call(box, text);
      box.dispatchEvent(new Event("input", { bubbles: true }));
      return;
    }
    if (document.hasFocus()) box.focus();
    document.execCommand("insertText", false, text);
  }

  function send(box) {
    const btn = [...document.querySelectorAll("button")].find((b) =>
      /send|submit/i.test(b.getAttribute("aria-label") || "") ||
      /send|submit/i.test(b.title || "") ||
      /send|submit/i.test(b.getAttribute("data-testid") || ""));
    if (btn) {
      btn.click();
      return;
    }
    for (const type of ["keydown", "keypress", "keyup"]) {
      box.dispatchEvent(new KeyboardEvent(type, {
        key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true,
      }));
    }
  }

  async function check() {
    if (paused()) return;
    if (busy()) return;
    const now = Date.now();
    if (now - Number(localStorage.getItem(KEY_LAST_FIRE) || 0) < COOLDOWN_MS) return;
    let state;
    try {
      const res = await fetch(RAW + "?t=" + now, { cache: "no-store" });
      if (!res.ok) return;
      state = await res.json();
    } catch (err) {
      return;
    }
    if (!state || !state.pending) return;
    if (state.id && state.id === localStorage.getItem(KEY_LAST_ID)) return;
    const box = composer();
    if (!box) return;
    if (hasDraft(box)) return;
    if (state.id) localStorage.setItem(KEY_LAST_ID, state.id);
    localStorage.setItem(KEY_LAST_FIRE, String(now));
    const text =
      `[wake ${state.id}] ${state.reason}\n\n` +
      `Read agent/STANDING_ORDERS.md and follow it in full. ` +
      `Work to the stop condition. Do not merge.`;
    type(box, text);
    setTimeout(() => send(box), 400);
  }

  badge();
  setInterval(check, POLL_MS);
  check();
})();
