(function () {
  "use strict";

  const API_URL = "/chat";
  const MAX_LEN = 500;

  const chatLog   = document.getElementById("chat-log");
  const chatForm  = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const sendBtn   = document.getElementById("send-btn");
  const charSpan  = document.getElementById("char-current");

  let history = [];
  let busy = false;

  /* ---- helpers ---- */

  function scrollToBottom() {
    requestAnimationFrame(() => {
      chatLog.scrollTop = chatLog.scrollHeight;
    });
  }

  function escapeHtml(text) {
    const d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
  }

  /* ---- render messages ---- */

  function addUserMsg(text) {
    const row = document.createElement("div");
    row.className = "msg-row user";
    row.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
    chatLog.appendChild(row);
    scrollToBottom();
  }

  function showTyping() {
    const el = document.createElement("div");
    el.className = "typing-indicator";
    el.id = "typing";
    el.innerHTML = `<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>`;
    chatLog.appendChild(el);
    scrollToBottom();
  }

  function removeTyping() {
    const el = document.getElementById("typing");
    if (el) el.remove();
  }

  function addBotMsg(text, meta) {
    const row = document.createElement("div");
    row.className = "msg-row bot";

    const guardClass = meta.guardrail_ok ? "passed" : "blocked";
    const guardLabel = meta.guardrail_ok ? "passed" : "blocked";

    row.innerHTML = `
      <div class="msg-bubble">${escapeHtml(text)}</div>
      <div class="msg-meta">
        <span class="meta-route">${escapeHtml(meta.route)}</span>
        <span class="meta-latency">${meta.latency.toFixed(2)}s</span>
        <span class="meta-guard ${guardClass}">${guardLabel}</span>
      </div>
    `;
    chatLog.appendChild(row);
    scrollToBottom();
  }

  function addErrorMsg(errText) {
    const row = document.createElement("div");
    row.className = "msg-row bot";
    row.innerHTML = `<div class="msg-bubble" style="border-color:var(--guard-block);color:var(--guard-block);">${escapeHtml(errText)}</div>`;
    chatLog.appendChild(row);
    scrollToBottom();
  }

  /* ---- auto-resize textarea ---- */

  chatInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 80) + "px";
    charSpan.textContent = this.value.length;
  });

  /* ---- submit ---- */

  chatForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    if (busy) return;

    const text = chatInput.value.trim();
    if (!text || text.length > MAX_LEN) return;

    busy = true;
    sendBtn.disabled = true;
    chatInput.value = "";
    chatInput.style.height = "auto";
    charSpan.textContent = "0";

    addUserMsg(text);
    showTyping();

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: history }),
      });

      removeTyping();

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        addErrorMsg(errData?.error || "Request failed — try again.");
      } else {
        const data = await res.json();
        addBotMsg(data.response, {
          route: data.route || "—",
          latency: data.latency || 0,
          guardrail_ok: data.guardrail_ok !== false,
        });

        history.push({ role: "user", content: text });
        history.push({ role: "assistant", content: data.response });

        // Keep history window manageable
        if (history.length > 20) {
          history = history.slice(-20);
        }
      }
    } catch (err) {
      removeTyping();
      addErrorMsg("Connection error — check if the server is running.");
    }

    busy = false;
    sendBtn.disabled = false;
    chatInput.focus();
  });

  /* ---- enter to send, shift+enter for newline ---- */

  chatInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  /* ---- initial focus ---- */
  chatInput.focus();
})();
