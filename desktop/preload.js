// The few things the game may ask the desktop app to do.
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('kumiteDesktop', {
  quit: () => ipcRenderer.send('quit'),
  toggleFullScreen: () => ipcRenderer.send('fullscreen'),
  isFullScreen: () => ipcRenderer.sendSync('isFullScreen'),
});
