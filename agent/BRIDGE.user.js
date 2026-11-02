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
@@APPEND@@
