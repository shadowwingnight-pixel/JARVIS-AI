"""A voice and text JARVIS assistant using Ollama locally."""

import ollama
import pyttsx3
import speech_recognition as sr

from command_router import CommandRouter
from memory_store import MemoryStore


MICROPHONE_DEVICE_INDEX = 30
MODEL_NAME = "qwen2.5:3b-instruct"
ASSISTANT_INSTRUCTIONS = (
	"You are JARVIS, a friendly, calm, and helpful assistant. "
	"Give clear beginner-friendly answers and keep responses concise."
)


def speak(text, speaker):
	"""Speak a response while keeping the text output visible."""
	speaker.say(text)
	speaker.runAndWait()


def listen_for_input(recognizer, microphone):
	"""Capture one voice request from the configured microphone."""
	try:
		with microphone as source:
			print("Listening...")
			audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
		print("Recognizing...")
		return recognizer.recognize_google(audio, language="en-IN").strip()
	except sr.WaitTimeoutError:
		print("JARVIS: I did not hear anything.")
	except sr.UnknownValueError:
		print("JARVIS: I could not understand that.")
	except sr.RequestError as error:
		print(f"JARVIS: Speech recognition is unavailable: {error}")
	return ""


def build_messages(conversation_history, user_input, memory_store, web_context=None):
	"""Build the Ollama messages with only memories relevant to this request."""
	relevant_memories = memory_store.search_memories(user_input)
	instructions = ASSISTANT_INSTRUCTIONS
	if relevant_memories:
		memory_text = "\n".join(
			f"- {memory['content']}" for memory in relevant_memories
		)
		instructions += (
			"\n\nRelevant memories the user explicitly asked you to save:\n"
			f"{memory_text}\n"
			"Use these only when they help answer the current request."
		)
	if web_context:
		instructions += f"\n\n{web_context}"
	return [{"role": "system", "content": instructions}, *conversation_history]


def main():
	conversation_history = []
	memory_store = MemoryStore()
	command_router = CommandRouter(memory_store)
	recognizer = sr.Recognizer()
	speaker = pyttsx3.init()
	microphone = sr.Microphone(device_index=MICROPHONE_DEVICE_INDEX)

	print("Choose input mode: [V]oice or [T]ext")
	mode = input("Mode: ").strip().lower()
	voice_mode = mode.startswith("v")
	if voice_mode:
		with microphone as source:
			print("Calibrating the Sony CH520 microphone...")
			recognizer.adjust_for_ambient_noise(source, duration=1)
		print("Voice mode ready. Say 'text mode' to switch modes.")
	else:
		print("Text mode ready. Type 'voice mode' to switch modes.")

	# Keep asking for input until the user chooses to stop.
	while True:
		if voice_mode:
			user_input = listen_for_input(recognizer, microphone)
		else:
			user_input = input("You: ").strip()

		# Convert the command to lowercase so EXIT and Exit also work.
		command = user_input.lower()

		if not user_input:
			continue

		command_result = command_router.handle(user_input)
		if command_result:
			print(f"JARVIS: {command_result.message}")
			speak(command_result.message, speaker)
			if command_result.should_exit:
				break
			if not command_result.web_context:
				continue
			web_context = command_result.web_context
		else:
			web_context = None

		if command in ("voice mode", "switch to voice", "switch to voice mode"):
			voice_mode = True
			with microphone as source:
				print("Calibrating the Sony CH520 microphone...")
				recognizer.adjust_for_ambient_noise(source, duration=1)
			print("JARVIS: Voice mode enabled.")
			continue

		if command in ("text mode", "switch to text", "switch to text mode"):
			voice_mode = False
			print("JARVIS: Text mode enabled.")
			continue

		# Save the user's message so later requests remember this conversation.
		conversation_history.append({"role": "user", "content": user_input})

		try:
			messages = build_messages(
				conversation_history, user_input, memory_store, web_context
			)
			if memory_store.last_error:
				print(f"JARVIS: {memory_store.last_error}")
			response = ollama.chat(
				model=MODEL_NAME,
				messages=messages,
			)
			assistant_message = response.message.content
			print(f"JARVIS: {assistant_message}")
			speak(assistant_message, speaker)

			# Save JARVIS's answer for the next request too.
			conversation_history.append(
				{"role": "assistant", "content": assistant_message}
			)
		except ollama.ResponseError as error:
			if error.status_code == 404:
				print(
					f"JARVIS: The Ollama model '{MODEL_NAME}' is unavailable. "
					f"Run: ollama pull {MODEL_NAME}"
				)
			else:
				print(f"JARVIS: Ollama returned an error: {error}")
			# Remove the unsent user message so a failed request does not
			# leave the conversation history out of sync.
			conversation_history.pop()
		except Exception as error:
			print(
				"JARVIS: I could not connect to Ollama. Make sure Ollama is running "
				f"and try again. Details: {error}"
			)
			# Remove the unsent user message so a temporary error does not
			# leave the conversation history out of sync.
			conversation_history.pop()


if __name__ == "__main__":
	main()
