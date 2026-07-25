// DispoHub Chat: WebSocket-Live-Empfang, Senden ohne Reload, Kamera/Galerie, Löschen.
(function () {
  const root = document.getElementById("chat");
  if (!root) return;

  const threadId = root.dataset.threadId;
  const meId = root.dataset.userId;
  const delWindowSec = parseInt(root.dataset.delWindow || "120", 10);
  if (!threadId) return;

  const list = document.getElementById("messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-text");
  const fileInput = document.getElementById("bild-input");
  const btnKamera = document.getElementById("btn-kamera");
  const btnGalerie = document.getElementById("btn-galerie");

  function scrollDown() {
    if (list) list.scrollTop = list.scrollHeight;
  }
  scrollDown();

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  // --- Kamera / Galerie: ein gemeinsames <input type=file>, unterschiedliches capture ---
  if (btnKamera && fileInput) {
    btnKamera.addEventListener("click", function () {
      fileInput.setAttribute("capture", "environment");
      fileInput.click();
    });
  }
  if (btnGalerie && fileInput) {
    btnGalerie.addEventListener("click", function () {
      fileInput.removeAttribute("capture");
      fileInput.click();
    });
  }
  if (fileInput) {
    fileInput.addEventListener("change", function () {
      if (fileInput.files && fileInput.files[0] && form) {
        // Direkt senden, sobald ein Bild gewählt/aufgenommen wurde.
        form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit", { cancelable: true }));
      }
    });
  }

  // --- Sprachnachricht: 🎤 einmal drücken = Aufnahme, nochmal = stoppen & senden ---
  const btnMikro = document.getElementById("btn-mikro");
  let recorder = null;
  let audioChunks = [];
  if (btnMikro && navigator.mediaDevices && window.MediaRecorder) {
    btnMikro.addEventListener("click", function () {
      if (recorder && recorder.state === "recording") {
        recorder.stop();
        return;
      }
      navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
        audioChunks = [];
        recorder = new MediaRecorder(stream);
        recorder.ondataavailable = function (e) { if (e.data.size) audioChunks.push(e.data); };
        recorder.onstop = function () {
          stream.getTracks().forEach(function (t) { t.stop(); });
          btnMikro.textContent = "🎤";
          btnMikro.classList.remove("recording");
          const blob = new Blob(audioChunks, { type: recorder.mimeType || "audio/webm" });
          if (blob.size < 200) return; // versehentlicher Doppelklick, nichts aufgenommen
          const fd = new FormData();
          fd.append("audio", blob, "sprachnachricht.webm");
          fd.append("text", "");
          fetch(form.action, { method: "POST", body: fd, headers: { "X-WS": "1" } });
        };
        recorder.start();
        btnMikro.textContent = "⏹️";
        btnMikro.classList.add("recording");
      }).catch(function () {
        alert("Mikrofon nicht verfügbar. Bitte Berechtigung im Browser erlauben.");
      });
    });
  } else if (btnMikro) {
    btnMikro.style.display = "none"; // Browser ohne Aufnahme-Unterstützung
  }

  // --- Löschen: eigene Nachricht, innerhalb des Zeitfensters ---
  function wireDeleteButton(btn) {
    if (!btn || btn.dataset.wired) return;
    btn.dataset.wired = "1";
    btn.addEventListener("click", function () {
      const id = btn.dataset.delId;
      if (!id) return;
      fetch("/chat/nachricht/" + id + "/loeschen", { method: "POST" }).then(function (r) {
        if (r.ok) markDeleted(id);
      });
    });
  }

  function markDeleted(id) {
    const bubble = document.querySelector('[data-mid="' + id + '"]');
    if (!bubble) return;
    bubble.classList.add("is-deleted");
    const img = bubble.querySelector(".bimg");
    if (img) img.closest("a").remove();
    const txt = bubble.querySelector(".txt");
    if (txt) txt.outerHTML = '<div class="txt deleted-txt">🚫 Nachricht gelöscht</div>';
    const actions = bubble.querySelector(".bubble-action");
    if (actions) actions.remove();
  }

  function updateDeleteButtonVisibility() {
    const now = Date.now();
    document.querySelectorAll(".bubble[data-mine='1']").forEach(function (bubble) {
      if (bubble.classList.contains("is-deleted")) return;
      const created = bubble.dataset.created;
      if (!created) return;
      const ageSec = (now - new Date(created).getTime()) / 1000;
      const btn = bubble.querySelector(".del-btn");
      if (!btn) return;
      if (ageSec <= delWindowSec) {
        btn.hidden = false;
        wireDeleteButton(btn);
      } else {
        btn.hidden = true;
      }
    });
  }
  updateDeleteButtonVisibility();
  setInterval(updateDeleteButtonVisibility, 5000);

  function addBubble(m) {
    if (!list) return;
    if (document.querySelector('[data-mid="' + m.id + '"]')) return; // Duplikat vermeiden
    const mine = String(m.sender_id) === String(meId);
    const el = document.createElement("div");
    el.className = "bubble " + (mine ? "mine" : "theirs");
    el.dataset.mid = m.id;
    el.dataset.mine = mine ? "1" : "0";
    el.dataset.created = new Date().toISOString();
    let html = "";
    if (!mine) html += '<div class="who">' + escapeHtml((m.sender_name || "").split(" ")[0]) + "</div>";
    if (m.image) html += '<a href="' + m.image + '" target="_blank"><img src="' + m.image + '" class="bimg"></a>';
    if (m.audio) html += '<audio controls preload="metadata" class="baudio" src="' + m.audio + '"></audio>';
    if (m.text) html += '<div class="txt">' + escapeHtml(m.text) + "</div>";
    html += '<div class="time">' + (m.time || "") + "</div>";
    if (mine) {
      html += '<div class="bubble-action"><button type="button" class="btn ghost sm del-btn" data-del-id="' +
        m.id + '">🗑️ Löschen</button></div>';
    }
    el.innerHTML = html;
    list.appendChild(el);
    scrollDown();
    if (mine) wireDeleteButton(el.querySelector(".del-btn"));

    if (!mine) {
      if (typeof fhPlayPing === "function") fhPlayPing();
      if (typeof fhNotify === "function") {
        const notifyVoice = (form && form.dataset.notifyVoice) || "🎤 Sprachnachricht";
        const notifyPhoto = (form && form.dataset.notifyPhoto) || "📷 Bild gesendet";
        fhNotify(m.sender_name || "Neue Nachricht",
                 m.text || (m.audio ? notifyVoice : notifyPhoto));
      }
    }
  }

  // WebSocket verbinden (mit einfachem Reconnect)
  let ws;
  function connect() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(proto + "//" + location.host + "/ws/chat/" + threadId);
    ws.onmessage = function (ev) {
      try {
        const m = JSON.parse(ev.data);
        if (m.type === "message") addBubble(m);
        if (m.type === "delete") markDeleted(m.id);
      } catch (e) {}
    };
    ws.onclose = function () {
      setTimeout(connect, 2000);
    };
  }
  connect();

  // Senden per fetch (kein Seiten-Reload)
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      const fd = new FormData(form);
      const hasText = (fd.get("text") || "").toString().trim().length > 0;
      const bild = fd.get("bild");
      const hasFile = bild && bild.name;
      if (!hasText && !hasFile) return;
      fetch(form.action, { method: "POST", body: fd, headers: { "X-WS": "1" } })
        .then(function () {
          if (input) input.value = "";
          if (fileInput) fileInput.value = "";
        });
    });
  }
})();
