// Browser-Benachrichtigungen + Ton bei neuen Chat-Nachrichten (opt-in).
function fhRequestNotificationPermission() {
  if (!("Notification" in window)) return;
  Notification.requestPermission().then(fhUpdateNotifyLabel);
}

function fhUpdateNotifyLabel() {
  var granted = "Notification" in window && Notification.permission === "granted";
  document.querySelectorAll(".notify-toggle-label").forEach(function (el) {
    el.textContent = granted ? "🔔" : "🔕";
  });
}

function fhNotify(title, body) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  if (document.visibilityState === "visible" && document.hasFocus()) return; // schon im Blick
  try {
    new Notification(title, { body: body, icon: "/static/icons/icon.svg" });
  } catch (e) {}
}

// Kurzer Ton per Web Audio API - kein Sound-Asset nötig.
function fhPlayPing() {
  try {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    var ctx = new Ctx();
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
    osc.start();
    osc.stop(ctx.currentTime + 0.25);
  } catch (e) {}
}

document.addEventListener("DOMContentLoaded", fhUpdateNotifyLabel);
