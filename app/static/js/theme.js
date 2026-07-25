// Theme (hell/dunkel): sofort anwenden (vor dem ersten Rendern, kein Geflacker),
// per Klick umschaltbar, in localStorage gemerkt - gilt für alle Rollen.
(function () {
  var stored = localStorage.getItem("fh-theme");
  if (stored) document.documentElement.setAttribute("data-theme", stored);
})();

function fhToggleTheme() {
  var current = document.documentElement.getAttribute("data-theme") || "light";
  var next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("fh-theme", next);
  fhUpdateThemeLabels(next);
}

function fhUpdateThemeLabels(theme) {
  document.querySelectorAll(".theme-toggle-label").forEach(function (el) {
    el.textContent = theme === "dark" ? "☀️" : "🌙";
  });
}

document.addEventListener("DOMContentLoaded", function () {
  var stored = localStorage.getItem("fh-theme") || "light";
  fhUpdateThemeLabels(stored);
});
