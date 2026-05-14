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

  function parseSseEvents(buffer) {
    const events = [];
    const blocks = buffer.split("\n\n");
    const remaining = blocks.pop() || "";

    for (const block of blocks) {
      const event = { type: "message", data: "" };
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) {
          event.type = line.slice(7);
        } else if (line.startsWith("data: ")) {
          event.data += line.slice(6);
        }
      }
      events.push(event);
    }

    return { events, remaining };
  }

  async function handleStreamResponse(resp, insertAt, originalNote) {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    const before = originalNote.slice(0, insertAt);
    const after = originalNote.slice(insertAt);
    let streamedCompletion = "";
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

      const parsed = parseSseEvents(buffer);
      buffer = parsed.remaining;

      for (const event of parsed.events) {
        const data = event.data ? JSON.parse(event.data) : "";

        if (event.type === "chunk") {
          streamedCompletion += data;
          noteEl.value = before + streamedCompletion + after;
          updateCharCount();

          const newCursorPos = insertAt + streamedCompletion.length;
          noteEl.focus();
          noteEl.setSelectionRange(newCursorPos, newCursorPos);
        } else if (event.type === "error") {
          throw new Error(data || "Something went wrong while streaming.");
        } else if (event.type === "done") {
          return streamedCompletion;
        }
      }

      if (done) {
        return streamedCompletion;
      }
    }
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
    continueBtn.textContent = "Streaming…";
    setStatus("Streaming AI continuation…", "info");

    try {
      const resp = await fetch("/api/complete/stream", {
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

      if (!resp.ok) {
        const data = await resp.json();
        console.error("API error:", data);
        setStatus(data.error || "Something went wrong.", "error");
        return;
      }

      const completion = await handleStreamResponse(resp, insertAt, note);
      if (!completion.trim()) {
        setStatus("AI returned an empty continuation.", "error");
        return;
      }

      setStatus("Continuation streamed and inserted.", "success");
    } catch (err) {
      console.error("Request failed:", err);
      setStatus(err.message || "Network error – could not reach the server.", "error");
    } finally {
      continueBtn.disabled = false;
      continueBtn.textContent = "✨ Continue with AI";
    }
  }

  continueBtn.addEventListener("click", handleContinueClick);
});
