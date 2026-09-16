# JARVIS-AI

A beginner-friendly terminal assistant using local Ollama, optional voice I/O,
explicit local memory, and safe command routing.

## Web search setup

Web search is optional and runs only for an explicit command such as:

```text
search the web for current Python release
web search latest weather in Mumbai
what is the latest news about space exploration
```

JARVIS uses the [Brave Search API](https://api.search.brave.com/). Create an
API key in the Brave dashboard, then add it to the project-local `.env` file:

```text
BRAVE_SEARCH_API_KEY=your_real_key
```

You can copy `.env.example` as a starting point. Alternatively, set
`BRAVE_SEARCH_API_KEY` in the Windows environment before starting JARVIS. The
real environment variable takes precedence over `.env`.

The key is never printed or committed. Search sends only the explicitly
requested query to Brave; saved JARVIS memories are never included in a search
request. Search results are passed to the local Ollama model as clearly labeled
current, untrusted source excerpts for summarization.

If the key is missing, the network is unavailable, the API times out, or there
are no results, JARVIS reports the issue without ending the conversation.

## Desktop GUI

Launch the optional Windows desktop interface with:

```powershell
python jarvis_gui.py
```

The GUI uses Tkinter from Python's standard library. Ollama, microphone input,
speech output, and system-information refreshes run in background threads so
the window remains responsive. The existing terminal interface remains
available through `python main.py`.
