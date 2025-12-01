import os
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Configure Ollama
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def call_ollama(model: str, system_prompt: str, user_prompt: str) -> str:
    """
    Call Ollama's /api/chat endpoint and return the assistant's content.
    """
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Error calling Ollama: {e}")

    data = resp.json()
    # Newer Ollama chat formats typically have message -> content
    message = data.get("message") or {}
    content = message.get("content", "")
    return content.strip()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", ollama_model=OLLAMA_MODEL)


@app.route("/api/complete", methods=["POST"])
def api_complete():
    """
    Request body JSON:
    {
      "note": "...",
      "selection_start": 10,
      "selection_end": 30
    }

    Returns:
    {
      "completion": "..."
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    note = data.get("note", "")
    sel_start = data.get("selection_start")
    sel_end = data.get("selection_end")

    if not isinstance(note, str) or note.strip() == "":
        return jsonify({"error": "Note cannot be empty."}), 400

    # Fallback if front-end didn’t send proper indices
    if not isinstance(sel_start, int) or not isinstance(sel_end, int):
        sel_start = 0
        sel_end = len(note)

    # Clamp indices
    sel_start = max(0, min(sel_start, len(note)))
    sel_end = max(0, min(sel_end, len(note)))

    has_selection = sel_end > sel_start

    if has_selection:
        context_text = note[sel_start:sel_end]
    else:
        context_text = note

    system_prompt = (
        "You are an assistant that helps users continue their notes.\n"
        "Match the tone and style of the given text.\n"
        "Only output the continuation of the note.\n"
        "Do NOT repeat the existing text. Do NOT add explanations or headings.\n"
        "Write 1–3 paragraphs at most."
    )

    user_prompt = (
        "Here is the existing note text:\n\n"
        f"{context_text}\n\n"
        "Continue this note naturally from where it left off."
    )

    try:
        completion = call_ollama(OLLAMA_MODEL, system_prompt, user_prompt)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"completion": completion})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
