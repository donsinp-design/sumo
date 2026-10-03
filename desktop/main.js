// Kumite desktop app (the Steam build): a window that runs the game from the files packed inside the app.
// Online play and phone controllers use the website's server (see public/js/platform.js).
const { app, BrowserWindow, ipcMain, Menu, shell } = require('electron');
const path = require('path');
const fs = require('fs');

// Steam: tell Steam which game this is when launched outside the Steam client during testing
const appIdFile = path.join(process.resourcesPath || __dirname, 'steam_appid.txt');
if (fs.existsSync(appIdFile)) process.env.SteamAppId = fs.readFileSync(appIdFile, 'utf8').trim();

app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required'); // sound from the first frame
app.commandLine.appendSwitch('disable-renderer-backgrounding');
Menu.setApplicationMenu(null);

const prefsFile = () => path.join(app.getPath('userData'), 'window.json');
const loadPrefs = () => { try { return JSON.parse(fs.readFileSync(prefsFile(), 'utf8')); } catch (e) { return { fullscreen: true }; } };
const savePrefs = (p) => { try { fs.writeFileSync(prefsFile(), JSON.stringify(p)); } catch (e) { /* read-only disk */ } };

let win;
function create() {
  const prefs = loadPrefs();
  win = new BrowserWindow({
    width: 1600, height: 900, minWidth: 960, minHeight: 540, backgroundColor: '#000000', show: false,
    fullscreen: !!prefs.fullscreen, autoHideMenuBar: true, title: 'Kumite',
    icon: path.join(__dirname, 'app', 'assets', 'icon-512.png'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, backgroundThrottling: false, spellcheck: false },
  });
  win.once('ready-to-show', () => win.show());
  win.loadFile(path.join(__dirname, 'app', 'index.html'));
  // F11 / Alt+Enter: fullscreen; links to websites open in the normal browser
  win.webContents.on('before-input-event', (e, i) => {
    if (i.type === 'keyDown' && (i.key === 'F11' || (i.alt && i.key === 'Enter'))) { toggle(); e.preventDefault(); }
  });
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  win.on('enter-full-screen', () => savePrefs({ fullscreen: true }));
  win.on('leave-full-screen', () => savePrefs({ fullscreen: false }));
}
const toggle = () => win && win.setFullScreen(!win.isFullScreen());

ipcMain.on('quit', () => app.quit());
ipcMain.on('fullscreen', () => toggle());
ipcMain.on('isFullScreen', (e) => { e.returnValue = !!(win && win.isFullScreen()); });

app.whenReady().then(create);
app.on('window-all-closed', () => app.quit());
