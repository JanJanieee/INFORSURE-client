"use strict";

// Toolbar click ang magbubukas sa side panel.
chrome.runtime.onInstalled.addListener(() => { /* Buksan ang panel kapag pinindot ang toolbar icon. */
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(/* I-log kung hindi na-set ang panel behavior. */ (error) => console.error(error));
});
