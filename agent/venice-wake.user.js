// Venice wake - watches for a WAKE.json flag and submits the prompt itself.
// Install in Tampermonkey or Violentmonkey. Keep this chat open in a tab.
// It polls: this is not a push. A server cannot reach the chat, a script in the page can.

// ==UserScript==
// @name         Venice wake
// @match        https://venice.ai/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  "use strict";
  const BRANCH = "venice/calendar-announce-ledger";
  const RAW = `https://raw.githubusercontent.com/SRoyaltyy/checklist-engine/${BRANCH}/agent/WAKE.json`;
  const POLL_MS = 60000;
  const COOLDOWN_MS = 5 * 60000;

  let lastFired = 0;
  let seenId = "";

  async function check() {
    if (Date.now() - lastFired < COOLDOWN_MS) return;
    let state;
    try {
      const res = await fetch(RAW + "?t=" + Date.now(), { cache: "no-store" });
      if (!res.ok) return;
      state = await res.json();
    } catch (err) {
      return;
    }
    if (!state || !state.pending) return;
    if (state.id && state.id === seenId) return;
    seenId = state.id || String(Date.now());
    lastFired = Date.now();
    fire(state);
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

  function fire(state) {
    const text =
      `[wake ${state.id}] ${state.reason}\n\n` +
      `Check what changed on the repo, then continue. Do not merge.`;
    const box = composer();
    if (!box) return;
    if (box.tagName === "TEXTAREA") {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
      setter.call(box, text);
      box.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      box.focus();
      document.execCommand("insertText", false, text);
    }
    setTimeout(() => {
      const btn = [...document.querySelectorAll("button")].find((b) =>
        /send/i.test(b.getAttribute("aria-label") || "") || /send/i.test(b.title || ""));
      if (btn) btn.click();
      else box.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    }, 400);
  }

  setInterval(check, POLL_MS);
  check();
})();