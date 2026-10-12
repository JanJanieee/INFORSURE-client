"use strict";

// Runs in every page. It only forwards the highlighted text to this extension's own side panel.
// Nothing is sent to the InforSure server until the user checks the text in the panel.
// The panel may also inject this file into a tab that was open before the extension, so guard against double loading.
(() => {
  if (window.__infosureContentLoaded) return;
  window.__infosureContentLoaded = true;

  let timer = null;
  let lastSent = "";

  function currentSelection() {
    return String(window.getSelection() || "").trim();
  }

  function report() {
    const text = currentSelection();
    if (!text || text === lastSent) return; // an emptied selection does not clear the panel
    lastSent = text;
    try {
      // Rejects when the panel is closed or the extension was reloaded; both are fine.
      chrome.runtime.sendMessage({ type: "infosure-selection", text }).catch(() => {});
    } catch (error) {
      /* extension context invalidated */
    }
  }

  document.addEventListener("selectionchange", () => {
    clearTimeout(timer);
    timer = setTimeout(report, 200);
  });

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message) return;
    if (message.type === "infosure-ping") sendResponse({ ok: true });
    if (message.type === "infosure-get-selection") {
      lastSent = ""; // the panel is asking, so the next change must be reported again
      sendResponse({ text: currentSelection() });
    }
  });
})();
