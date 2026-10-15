"use strict";

// I-forward ang page selection sa sariling side panel.
// Walang analysis request hanggat hindi pina-check ang claim.
// Iwasan ang dobleng listeners kapag na-inject ulit.
(() => { /* Ihanda ang selection listeners nang isang beses lang. */
  if (window.__infosureContentLoaded) return;
  window.__infosureContentLoaded = true;

  let timer = null;
  let lastSent = "";

  // Kunin ang highlighted text sa page.
  function currentSelection() {
    return String(window.getSelection() || "").trim();
  }

  // Ipadala ang bagong selection sa side panel.
  function report() {
    const text = currentSelection();
    if (!text || text === lastSent) return; // Panatilihin ang panel text kung blank ang selection.
    lastSent = text;
    try {
      // Normal lang kung sarado ang panel o na-reload ang extension.
      chrome.runtime.sendMessage({ type: "infosure-selection", text }).catch(() => { /* Puwedeng walang receiver kapag sarado ang panel. */});
    } catch (error) {
      /* Na-reload o naalis ang extension context. */
    }
  }

  document.addEventListener("selectionchange", () => { /* Hintaying matapos ang pagpili bago mag-report. */
    clearTimeout(timer);
    timer = setTimeout(report, 200);
  });

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => { /* Sagutin ang ping at selection requests. */
    if (!message) return;
    if (message.type === "infosure-ping") sendResponse({ ok: true });
    if (message.type === "infosure-get-selection") {
      lastSent = ""; // I-report ulit ang susunod na selection change.
      sendResponse({ text: currentSelection() });
    }
  });
})();
