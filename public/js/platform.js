'use strict';
// Where the game is running: the website, the desktop app (Steam: Electron) or the iPhone / iPad / Mac app
// (Capacitor). Apps load the game from inside the app, so online play and phone controllers talk to the
// website's server instead of "the page's own address".
(function () {
  const web = location.protocol === 'http:' || location.protocol === 'https:';
  const cap = !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform());
  S.APP = window.kumiteDesktop ? 'desktop' : cap ? 'ios' : web ? 'web' : 'desktop';
  // portal builds (itch.io, Newgrounds, ...) are hosted elsewhere and set KUMITE_SERVER to the real server
  S.PORTAL = window.KUMITE_PORTAL || '';
  S.SERVER = window.KUMITE_SERVER || (S.APP === 'web' ? new URL('./', location.href).toString() : 'https://looktwicestudio.com/kumite/');
  // a websocket address on the game server, e.g. S.wsUrl('ws') -> wss://looktwicestudio.com/kumite/ws
  S.wsUrl = (path) => { const u = new URL(path, S.SERVER); u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:'; u.search = ''; u.hash = ''; return u; };
  S.webUrl = (path) => new URL(path, S.SERVER).toString();
  if (S.APP !== 'web') document.documentElement.classList.add('app', 'app-' + S.APP);
})();
