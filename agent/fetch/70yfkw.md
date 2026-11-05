# FETCH https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/LOADER2.user.js

fetched 2026-11-05T11:38:22.478Z status 200 ua Mozilla/5.0 venice-doorman

checklist-engine/agent/LOADER2.user.js at venice/sec-options-pipelines · SRoyaltyy/checklist-engine · GitHub 

 
 
 
 

 
 

 

 

 
 

 
 

 

 

 

 

 

 

 

 

 

 

 
 
 

 
 
 

 

 

 
 
 
 

 

 

 

 

 
 

 

 
 

 

 

 
 

 
 
 

 
 

 

 

 
 
 
 

 
 Skip to content 

 
 
 
 
 
 
 

 
 
 
 
 

 

 
 
 

 
 
 
 
 

 

 
 
 
 
 
 
 
 
 
 
 
 

 
 
 
 Navigation Menu Sign in Products Platform GitHub Repository hosting, code review, and collaboration Copilot AI coding agent for tasks, projects and automated work Build & Ship Actions CI/CD and automation Code Quality Quality analysis, fixes, and enforcement Codespaces Cloud development environments Secure Code Security Vulnerability detection and remediation Secret Protection Secret scanning and leak prevention All Features Developers Learn Documentation Training Certifications Build Build with Copilot Customize Copilot Integrations Explore Trending repos GitHub Sponsors Developer articles Changelog Changelog Your source for the latest features, improvements, and fixes across GitHub products, all in one place. Businesses By Stage Enterprises Team Startups Nonprofits By Industry Healthcare Financial services Manufacturing Government See all industries Evaluate GitHub Why GitHub Customer Stories Business insights Trust Center Add-ons GitHub Advanced Security Enterprise-grade code security Copilot for business Enterprise-grade AI features Premium Support Enterprise-grade 24/7 support Resources Learn & Connect Documentation Resource center Blog Events & webinars Community Forum Customer Stories Integrations Support Customer support Training GitHub Status Company About Partners Changelog GitHub Universe GitHub Universe The event for developers, by developers — talks, workshops, and what’s next for GitHub. Pricing Search / Sign in Sign up Appearance settings 
 

 
 
 
 
 
 You signed in with another tab or window. Reload to refresh your session. 
 You signed out in another tab or window. Reload to refresh your session. 
 You switched accounts on another tab or window. Reload to refresh your session. 

 
 
 
 Dismiss alert 

 
 
 

 

 

 
 
 
 
 
 
 
 
 
 
 
 {{ message }} 

 
 
 
 
 

 

 
 
 
 
 

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 

 
 
 
 SRoyaltyy checklist-engine Repository navigation Code Issues Pull requests 47  ( 47 ) Actions Projects Security and quality Insights More items 
 

 

 
 
 

 
 
 

 
 
 
 Files Expand file tree venice/sec-options-pipelines Breadcrumbs checklist-engine / agent / LOADER2.user.js Copy path Blame More file actions Blame More file actions Latest commit   History History History 158 lines (142 loc) · 5.31 KB venice/sec-options-pipelines Breadcrumbs checklist-engine / agent / LOADER2.user.js Copy path Top File metadata and controls Code Blame 158 lines (142 loc) · 5.31 KB Raw Copy raw file Download raw file Open symbols panel Edit and raw actions 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 // ==UserScript== // @name Venice Bridge Loader // @namespace venice.local // @version 1.8 // @match https://venice.ai/* // @grant GM_xmlhttpRequest // @grant GM_setValue // @grant GM_getValue // @connect venice-doorman.fullscan-relay.workers.dev // @run -at document-idle // ==/UserScript== 
 ( function ( ) { &#039;use strict&#039; ; var W = &#039;https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=&#039; ; var BR = &#039;venice%2Fsec-options-pipelines&#039; ; var KEY = &#039;vrb.lastgood&#039; , VER = &#039;vrb.version&#039; , BAD = &#039;vrb.bad&#039; ; var SETTLE_MS = 120000 ; 
 var mine = document . createElement ( &#039;div&#039; ) ; mine . style . cssText = &#039;position:fixed;right:14px;bottom:14px;z-index:2147483646;padding:7px 11px;border-radius:8px;font:12px ui-monospace,monospace;color:#fff;background:#9e6a03;cursor:default;box-shadow:0 2px 10px rgba(0,0,0,.45);opacity:.9;&#039; ; mine . textContent = &#039;LOAD v1.8&#039; ; function say ( t , bg ) { mine . textContent = t ; mine . style . background = bg ; } function show ( ) { if ( ! mine . parentElement && document . body ) document . body . appendChild ( mine ) ; } function hide ( ) { if ( mine . parentElement ) mine . remove ( ) ; } 
 function hash ( s ) { var h = 5381 , i ; s = String ( s ) ; for ( i = 0 ; i < s . length ; i ++ ) h = ( ( h * 33 ) ^ s . charCodeAt ( i ) ) >>> 0 ; return h . toString ( 36 ) + &#039;.&#039; + s . length . toString ( 36 ) ; } 
 function patch ( src ) { var out = String ( src ) , n = 0 ; if ( out . indexOf ( "wake(reason || &#039;heartbeat&#039;, false)" ) !== - 1 ) { out = out . replace ( "wake(reason || &#039;heartbeat&#039;, false)" , "wake(reason || &#039;heartbeat&#039;, true)" ) ; n ++ ; } if ( out . indexOf ( &#039;@version 5.1&#039; ) !== - 1 ) { out = out . replace ( &#039;@version 5.1&#039; , &#039;@version 5.4&#039; ) ; n ++ ; } if ( out . indexOf ( "var text = document.body.innerText || &#039;&#039;" ) !== - 1 ) { out = out . replace ( "var text = document.body.innerText || &#039;&#039;" , "var text = (document.body.innerText || &#039;&#039;).slice(-20000)" ) ; n ++ ; } if ( n ) console . log ( &#039;[loader] patched &#039; + n + &#039; spot(s)&#039; ) ; return out ; } 
 function get ( p ) { return new Promise ( function ( res ) { GM_xmlhttpRequest ( { method : &#039;GET&#039; , timeout : 20000 , url : W + &#039;read&branch=&#039; + BR + &#039;&path=&#039; + encodeURIComponent ( p ) + &#039;&t=&#039; + Date . now ( ) , onload : function ( r ) { res ( r . status >= 200 && r . status < 300 ? r . responseText : &#039;&#039; ) ; } , onerror : function ( ) { res ( &#039;&#039; ) ; } , ontimeout : function ( ) { res ( &#039;&#039; ) ; } } ) ; } ) ; } 
 function unwrap ( raw ) { try { var o = JSON . parse ( raw ) ; if ( o && typeof o . text === &#039;string&#039; ) return o . text ; } catch ( e ) { } return raw ; } 
 function sanitize ( src ) { return String ( src ) . replace ( / ^ \s * C o p y c o d e \s * $ / gm , &#039;&#039; ) . replace ( / ^ \s * C o p i e d \s * $ / gm , &#039;&#039; ) . replace ( / ^ \s * ` ` ` [ a - z 0 - 9 + # . _ - ] * \s * $ / gmi , &#039;&#039; ) ; } 
 function stopOld ( ) { try { if ( window . __vrb && window . __vrb . stop ) window . __vrb . stop ( ) ; } catch ( e ) { } window . __vrb = null ; } 
 function badList ( ) { try { return JSON . parse ( GM_getValue ( BAD , &#039;[]&#039; ) ) || [ ] ; } catch ( e ) { return [ ] ; } } function markBad ( v ) { if ( ! v ) return ; var l = badList ( ) ; if ( l . indexOf ( v ) === - 1 ) l . push ( v ) ; GM_setValue ( BAD , JSON . stringify ( l . slice ( - 20 ) ) ) ; } 
 var settleTimer = null ; function cancelSettle ( ) { if ( settleTimer ) { clearTimeout ( settleTimer ) ; settleTimer = null ; } } 
 function healthy ( ) { return ! ! ( window . __vrb && window . __vrb . stop ) ; } 
 function boot ( rawSrc , tag , version , retry ) { var src = patch ( sanitize ( rawSrc ) ) ; if ( version && badList ( ) . indexOf ( version ) !== - 1 ) { say ( &#039;SKIP BAD &#039; + version , &#039;#9e6a03&#039; ) ; return false ; } stopOld ( ) ; cancelSettle ( ) ; try { new Function ( &#039;GM_xmlhttpRequest&#039; , src ) ( GM_xmlhttpRequest ) ; } catch ( e ) { say ( &#039;EVAL FAIL&#039; , &#039;#d1242f&#039; ) ; console . log ( &#039;[loader] eval failed&#039; , e ) ; markBad ( version ) ; return false ; } say ( &#039;LOADED &#039; + ( tag || &#039;&#039; ) , &#039;#238636&#039; ) ; settleTimer = setTimeout ( function ( ) { if ( healthy ( ) ) { hide ( ) ; return ; } if ( ! retry ) { say ( &#039;UNHEALTHY, RETRY&#039; , &#039;#9e6a03&#039; ) ; console . log ( &#039;[loader] build &#039; + ( version || tag ) + &#039; unhealthy, one retry&#039; ) ; boot ( rawSrc , tag , version , true ) ; return ; } say ( &#039;UNHEALTHY, ROLLBACK&#039; , &#039;#d1242f&#039; ) ; console . log ( &#039;[loader] build &#039; + ( version || tag ) + &#039; unhealthy twice, rolling back&#039; ) ; markBad ( version ) ; var last = GM_getValue ( KEY , &#039;&#039; ) ; if ( last ) boot ( last , &#039;lastgood&#039; , &#039;&#039; ) ; else say ( &#039;NO FALLBACK&#039; , &#039;#d1242f&#039; ) ; } , SETTLE_MS ) ; console . log ( &#039;[loader] bridge started&#039; ) ; return true ; } 
 function adopt ( src , tag ) { var v = hash ( patch ( src ) ) ; if ( v === GM_getValue ( VER , &#039;&#039; ) ) return false ; if ( badList ( ) . indexOf ( v ) !== - 1 ) { say ( &#039;SKIP BAD&#039; , &#039;#9e6a03&#039; ) ; return false ; } if ( boot ( src , tag , v ) ) { GM_setValue ( KEY , src ) ; GM_setValue ( VER , v ) ; return true ; } return false ; } 
 function refresh ( ) { get ( &#039;agent/BRIDGE.user.js&#039; ) . then ( function ( raw ) { var src = unwrap ( raw ) ; if ( ! src || src . length < 500 ) return ; adopt ( src , hash ( patch ( src ) ) ) ; } ) ; } 
 show ( ) ; get ( &#039;agent/BRIDGE.user.js&#039; ) . then ( function ( raw ) { var src = unwrap ( raw ) ; if ( src && src . length > 500 && adopt ( src , &#039;init&#039; ) ) return ; var last = GM_getValue ( KEY , &#039;&#039; ) ; if ( last ) { console . log ( &#039;[loader] using last good&#039; ) ; boot ( last , &#039;cached&#039; , &#039;&#039; ) ; return ; } say ( &#039;NO SOURCE&#039; , &#039;#d1242f&#039; ) ; } ) ; 
 setInterval ( refresh , 60000 ) ; } ( ) ) ; 
 

 

 

 
 

 

 
 Footer 

 

 
 
 
 
 
 
 
 
 &copy; 2026 GitHub, Inc.
 
 

 
 Footer navigation 

 

 
 Terms 
 

 
 Privacy 
 

 
 Security 
 

 
 Status 
 

 
 Community 
 

 
 Docs 
 

 
 Contact 
 

 
 
 
 
 Manage cookies
 
 
 

 
 
 
 Do not share my personal information
 
 
 

 
 
 
 

 

 
 
 
 
 
 
 
 
 
 You can’t perform that action at this time.
