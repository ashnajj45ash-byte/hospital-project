const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatWindow = document.getElementById("chat-window");

function appendMessage(text, sender) {
  const div = document.createElement("div");
  div.className = sender === "user" ? "user-msg" : "bot-msg";
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  appendMessage(message, "user");
  chatInput.value = "";
  appendMessage("Thinking...", "bot");
  const thinkingNode = chatWindow.lastChild;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();

    thinkingNode.remove();

    if (data.error) {
      appendMessage("Error: " + data.error, "bot");
    } else {
      appendMessage(data.answer, "bot");
    }
  } catch (err) {
    thinkingNode.remove();
    appendMessage("Something went wrong. Please try again.", "bot");
  }
});