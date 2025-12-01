document.addEventListener("DOMContentLoaded", () => {
  const noteEl = document.getElementById("note");
  const charCountEl = document.getElementById("char-count");
  const continueBtn = document.getElementById("continue-btn");
  const statusEl = document.getElementById("status");

  function updateCharCount() {
    const len = noteEl.value.length;
    charCountEl.textContent = `${len} character${len === 1 ? "" : "s"}`;
  }

  noteEl.addEventListener("input", updateCharCount);
  updateCharCount();

  function setStatus(message, type = "info") {
    statusEl.textContent = message || "";
    statusEl.className = `status-line ${type}`;
  }

  async function handleContinueClick() {
    const note = noteEl.value;
    if (!note.trim()) {
      setStatus("Please type something in the note first.", "error");
      return;
    }

    const selectionStart = noteEl.selectionStart;
    const selectionEnd = noteEl.selectionEnd;

    const insertAt = selectionEnd;

    continueBtn.disabled = true;
    continueBtn.textContent = "Thinking…";
    setStatus("Calling AI to continue your note…", "info");

    try {
      const resp = await fetch("/api/complete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          note,
          selection_start: selectionStart,
          selection_end: selectionEnd
        })
      });

      const data = await resp.json();

      if (!resp.ok) {
        console.error("API error:", data);
        setStatus(data.error || "Something went wrong.", "error");
        continueBtn.disabled = false;
        continueBtn.textContent = "✨ Continue with AI";
        return;
      }

      const completion = data.completion || "";
      if (!completion.trim()) {
        setStatus("AI returned an empty continuation.", "error");
        continueBtn.disabled = false;
        continueBtn.textContent = "✨ Continue with AI";
        return;
      }

      const before = note.slice(0, insertAt);
      const after = note.slice(insertAt);

      const newText = before + completion + after;
      noteEl.value = newText;
      updateCharCount();

      const newCursorPos = insertAt + completion.length;
      noteEl.focus();
      noteEl.setSelectionRange(newCursorPos, newCursorPos);

      setStatus("Continuation inserted.", "success");
    } catch (err) {
      console.error("Request failed:", err);
      setStatus("Network error – could not reach the server.", "error");
    } finally {
      continueBtn.disabled = false;
      continueBtn.textContent = "✨ Continue with AI";
    }
  }

  continueBtn.addEventListener("click", handleContinueClick);
});
