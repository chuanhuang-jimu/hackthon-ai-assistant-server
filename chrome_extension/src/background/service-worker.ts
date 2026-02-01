console.log("Service worker has been loaded.");

chrome.runtime.onInstalled.addListener(() => {
  console.log("CRXJS React Vite App installed");
});
