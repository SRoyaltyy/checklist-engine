// ==UserScript==
// @name         Venice Repo Bridge
// @namespace    venice.local
// @version     4.1
// @match       https://venice.ai/*
// @grant       GM_xmlhttpRequest
// @connect     venice-doorman.fullscan-relay.workers.dev
// @run-at      document-idle
// ==/UserScript==

(function () {
  'use strict';
  var W = 'https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=';
  var BR = 'venice%2Fcalendar-announce-ledger';
  var REPO = 'SRoyaltyy/checklist-engine';
  var POLL = 30000, COOL = 240000, FAIL_LIMIT = 2, STUCK_MS = 150000, BOOT_MAX = 2;
  var READS = ['agent/BRIEF.md', 'agent/STANDING_ORDERS.md', 'agent/QUEUE.jsonl', 'agent/STATE.md', 'agent/PROGRESS.md', 'agent/JOURNAL.md', 'agent/TEST_LOG.txt', 'agent/GANTT_ROWS.md', 'agent/WAKE.json'];
  var BOOT_READS = ['agent/PROGRESS.md', 'agent/JOURNAL.md', 'agent/STATE.md', 'agent/QUEUE.jsonl', 'agent/GANTT_ROWS.md', 'agent/DOORMAN.worker.js', 'agent/DEPLOYER.worker.js'];
  var busy = false, sent = 0, phase = 'work', bootTries = 0, awaiting = 0, nodesAt = 0;
@@APPEND@@
