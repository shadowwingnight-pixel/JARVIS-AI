# JARVIS-AI contributor guide

## Project purpose

JARVIS-AI is a beginner-friendly, terminal-based Python assistant. It accepts
text or voice input, asks a locally running Ollama model for a reply, prints
the reply, and speaks it aloud.

The current default model is `qwen2.5:3b-instruct`. Keep the assistant calm,
helpful, concise, and easy for a beginner to understand.

## Current project layout

```text
main.py           Application entry point and current implementation
requirements.txt  Python runtime dependencies
AGENTS.md         Project rules and development guidance
command_router.py Explicit local command routing
web_search.py     Optional current-information web search client
config.py          Local environment configuration helper
system_control.py  Allowlisted local Windows system actions
assistant_backend.py UI-neutral conversation adapter
voice_service.py    UI-safe microphone and speech service
jarvis_gui.py       Optional Tkinter desktop interface
```

`main.py` currently owns the input loop, audio handling, conversation history,
Ollama request, error handling, and text-to-speech. This is appropriate for
the small prototype, but future features should be separated into focused
modules rather than making `main.py` indefinitely larger.

## Runtime dependencies

- `ollama`: Python client for a local Ollama server.
- `SpeechRecognition`: microphone capture and speech-to-text integration.
- `pyttsx3`: local text-to-speech through the operating system's speech engine.
- `PyAudio`: microphone/audio backend used by SpeechRecognition.

Optional web search uses the Brave Search API through Python's standard
library. Set `BRAVE_SEARCH_API_KEY` in `.env` or the process environment; see
`README.md` for setup. Never print, commit, or send this key to Ollama.

The machine must also have Ollama running and the configured model installed:

```powershell
ollama pull qwen2.5:3b-instruct
```

Voice recognition currently calls Google speech recognition with `en-IN`; it
therefore may require internet access even though language generation is local.

## Architecture guidelines

- Keep `main()` small: it should eventually assemble components and run the
  application loop, not contain every implementation detail.
- Preserve the current message format for Ollama: dictionaries with `role` and
  `content`, including one system instruction followed by conversation history.
- Keep user and assistant messages paired in history. If a model request fails,
  remove or otherwise mark the pending user message so history remains valid.
- Treat audio input, text input, model access, text-to-speech, configuration,
  and memory as separate responsibilities when extracting modules.
- Prefer configuration for machine-specific values such as microphone device,
  model name, language, timeouts, and whether replies are spoken. Do not add
  more hardware-specific constants to application logic.
- Keep a text-only path usable for development and troubleshooting when no
  microphone or audio driver is available.
- Bound conversation memory or persist it deliberately; do not allow an
  unbounded chat history to grow unnoticed.

## Safety and privacy rules

- Never commit secrets, API keys, personal recordings, or conversation logs.
  Keep local configuration in `.env`, which is already ignored by Git.
- Do not print configuration secrets or raw sensitive user input in errors or
  debug logs.
- Ask for clear user confirmation before adding actions that affect the system
  or external services, such as launching applications, changing files,
  sending messages, running shell commands, or making purchases.
- Default new capabilities to read-only behavior. Keep risky actions disabled
  until they have explicit confirmation, clear output, and safe error handling.
- Keep local system actions in `system_control.py` and expose them only through
  exact, allowlisted command-router phrases. Never pass model output to a
  shell, process launcher, URL opener, or screenshot command.
- Explain that Google-based speech recognition can send audio off-device. Do
  not describe the current voice-input path as fully offline.
- Web search may send an explicitly requested query to Brave Search. Do not
  include local memories or other private context in a search request.
- Handle microphone, network, model, and TTS failures gracefully. The program
  should return to a usable prompt whenever it is safe to do so.

## Coding conventions

- Target clear, beginner-friendly Python. Use descriptive names, small
  functions, docstrings for public helpers, and comments only where they add
  useful intent.
- Follow standard Python formatting: four spaces for indentation, `snake_case`
  names for functions and variables, and `UPPER_SNAKE_CASE` for constants.
- Keep user-facing messages consistent with the `JARVIS:` prefix and make
  recovery instructions actionable.
- Catch expected library exceptions as specifically as possible. Do not hide
  programming errors behind broad exception handling without reporting useful
  context.
- Add new Python packages to `requirements.txt`; pin versions once the project
  establishes a tested environment or release process.
- Do not change the configured model, microphone default, or recognition
  language casually: make such changes configurable and document their impact.
- Before submitting a change, at minimum run a syntax check and exercise text
  mode. Test voice mode on the intended audio hardware when audio code changes.

## Current development roadmap

1. **Configuration and onboarding**: add a README, document installation,
   create a configuration mechanism, and provide a microphone-device listing
   flow instead of relying on device index `30`.
2. **Reliability and testability**: split the current script into testable
   input, model, audio, and application modules; add unit tests and clearer
   diagnostics for Ollama, microphone, and TTS failures.
3. **Conversation memory**: local, explicit JSON memory is now available.
   Next, add a deliberate history limit, optional memory backup/export, and an
   easy way for users to clear stored data.
4. **Assistant capabilities**: an explicit command router now provides time,
   allowlisted app/URL opening, local system status, memory commands, optional
   web search, and exit. Next, add only clearly scoped, confirmed commands
   such as notes.
5. **Voice experience**: make speech settings configurable and evaluate
   optional offline speech-to-text and wake-word support while keeping text
   mode reliable.
6. **Desktop GUI**: the Tkinter interface now provides a dark JARVIS-inspired
   dashboard with chat, voice input, local Ollama status, clock, and system
   information. Future work can add settings, wake-word support, and optional
   animations without changing the backend interfaces.

## Change checklist

- Keep local Ollama support working with `qwen2.5:3b-instruct`.
- Keep both text and voice modes functional, or clearly document intentional
  behavior changes.
- Avoid committing generated files, virtual environments, local configuration,
  recordings, or user data.
- Update this guide and the README when architecture, setup, privacy behavior,
  or roadmap priorities materially change.
