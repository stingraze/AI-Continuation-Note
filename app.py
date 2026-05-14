import json
import os

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
import requests

app = Flask(__name__)

# Configure Ollama
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def build_prompts(note: str, sel_start: int | None, sel_end: int | None) -> tuple[str, str]:
    """
    Build the system and user prompts used to continue a note.
    """
    if not isinstance(sel_start, int) or not isinstance(sel_end, int):
        sel_start = 0
        sel_end = len(note)

    sel_start = max(0, min(sel_start, len(note)))
    sel_end = max(0, min(sel_end, len(note)))

    has_selection = sel_end > sel_start
    context_text = note[sel_start:sel_end] if has_selection else note

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

    return system_prompt, user_prompt


def build_ollama_payload(model: str, system_prompt: str, user_prompt: str, stream: bool) -> dict:
    """
    Build the payload for Ollama's /api/chat endpoint.
    """
    return {
        "model": model,
        "stream": stream,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }


def call_ollama(model: str, system_prompt: str, user_prompt: str) -> str:
    """
    Call Ollama's /api/chat endpoint and return the assistant's content.
    """
    url = f"{OLLAMA_HOST}/api/chat"
    payload = build_ollama_payload(model, system_prompt, user_prompt, stream=False)

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


def stream_ollama(model: str, system_prompt: str, user_prompt: str):
    """
    Stream assistant content chunks from Ollama's /api/chat endpoint.
    """
    url = f"{OLLAMA_HOST}/api/chat"
    payload = build_ollama_payload(model, system_prompt, user_prompt, stream=True)

    try:
        with requests.post(url, json=payload, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue

                data = json.loads(line)
                message = data.get("message") or {}
                content = message.get("content", "")
                if content:
                    yield content

                if data.get("done"):
                    break
    except (json.JSONDecodeError, requests.RequestException) as e:
        raise RuntimeError(f"Error streaming from Ollama: {e}")


def sse_event(event_type: str, data: str) -> str:
    """
    Format a server-sent event.
    """
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


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

    system_prompt, user_prompt = build_prompts(note, sel_start, sel_end)

    try:
        completion = call_ollama(OLLAMA_MODEL, system_prompt, user_prompt)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"completion": completion})


@app.route("/api/complete/stream", methods=["POST"])
def api_complete_stream():
    """
    Stream an Ollama note continuation as server-sent events.
    """
    data = request.get_json(force=True, silent=True) or {}
    note = data.get("note", "")
    sel_start = data.get("selection_start")
    sel_end = data.get("selection_end")

    if not isinstance(note, str) or note.strip() == "":
        return jsonify({"error": "Note cannot be empty."}), 400

    system_prompt, user_prompt = build_prompts(note, sel_start, sel_end)

    @stream_with_context
    def generate():
        try:
            streamed_any = False
            for chunk in stream_ollama(OLLAMA_MODEL, system_prompt, user_prompt):
                streamed_any = True
                yield sse_event("chunk", chunk)

            if not streamed_any:
                yield sse_event("error", "AI returned an empty continuation.")
                return

            yield sse_event("done", "")
        except RuntimeError as e:
            yield sse_event("error", str(e))

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
