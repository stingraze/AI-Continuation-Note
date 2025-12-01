# AI Continuation Note (Flask + Ollama)

A minimal notebook-style web app that continues your notes with a local Ollama model.

This is useful to writers who have written parts of a sentence but don't know the continutation. The AI will fill the rest for the writer in that case.

Created with the help of AI.

(C)Tsubasa Kato - 2025 - Inspire Search Corp.

![AI Continuation Note screenshot](https://github.com/stingraze/AI-Continuation-Note/blob/main/ai-continuation-note.jpg)

## Features

- Notebook UI in the browser
- Highlight a passage or just place the cursor
- Click "✨ Continue with AI" to let the model continue your note
- Uses Flask (Python 3) + Ollama `/api/chat` endpoint

## Setup

1. Make sure [Ollama](https://ollama.com/) is installed and running:

   ```bash
   ollama pull llama3.1:8b
   ollama serve
   ```

2. Create and activate a virtual environment, then install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. (Optional) Choose a different model:

   ```bash
   export OLLAMA_MODEL="llama3.1:8b"
   ```

4. Run the app:

   ```bash
   python app.py
   ```

5. Open your browser at:

   - http://localhost:5000

Start typing, highlight part of your note (or just place the cursor), and click **"✨ Continue with AI"**.
