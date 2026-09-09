(function () {
  const launcher = document.getElementById("cw-launcher");
  const panel = document.getElementById("cw-panel");
  const body = document.getElementById("cw-body");
  const form = document.getElementById("cw-form");
  const input = document.getElementById("cw-input");
  const sendBtn = document.getElementById("cw-send");
  const badge = document.getElementById("cw-badge");

  if (!launcher || !panel || !form) return;

  let opened = false;

  function setOpen(next) {
    opened = next;
    panel.classList.toggle("open", opened);
    launcher.classList.toggle("open", opened);
    launcher.setAttribute("aria-expanded", String(opened));
    if (opened) {
      badge.style.display = "none";
      input.focus();
      body.scrollTop = body.scrollHeight;
    }
  }

  launcher.addEventListener("click", () => setOpen(!opened));

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && opened) setOpen(false);
  });

  function appendMessage(text, sender) {
    const div = document.createElement("div");
    div.className = sender === "user" ? "user-msg" : "bot-msg";
    div.textContent = text;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
    return div;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    appendMessage(message, "user");
    input.value = "";
    sendBtn.disabled = true;

    const typingNode = appendMessage("Typing...", "bot");
    typingNode.classList.add("typing");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();

      typingNode.remove();

      if (data.error) {
        appendMessage("Error: " + data.error, "bot");
      } else {
        appendMessage(data.answer, "bot");
      }
    } catch (err) {
      typingNode.remove();
      appendMessage("Something went wrong. Please try again.", "bot");
    } finally {
      sendBtn.disabled = false;
    }
  });
})();