console.log("Content script loaded.");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "change-color") {
    const randomColor = "#" + Math.floor(Math.random()*16777215).toString(16);
    document.body.style.backgroundColor = randomColor;
    console.log(`Page background changed to: ${randomColor}`);
    sendResponse({ status: "Color changed" });
  }
  return true;
});
