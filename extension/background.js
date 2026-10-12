"use strict";

// Clicking the toolbar icon opens the side panel, which stays open while the user highlights text on the page.
chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch((error) => console.error(error));
});
