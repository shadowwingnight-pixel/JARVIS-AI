"""A simple text-based JARVIS assistant using Ollama locally."""

import ollama


def main():
	conversation_history = []
	model_name = "qwen2.5:3b-instruct"
	assistant_instructions = (
		"You are JARVIS, a friendly, calm, and helpful assistant. "
		"Give clear beginner-friendly answers and keep responses concise."
	)

	# Keep asking for input until the user chooses to stop.
	while True:
		user_input = input("You: ").strip()

		# Convert the command to lowercase so EXIT and Exit also work.
		command = user_input.lower()

		# Stop the program when the user enters an exit word.
		if command in ("exit", "quit", "bye"):
			print("JARVIS: Goodbye!")
			break

		if not user_input:
			continue

		# Save the user's message so later requests remember this conversation.
		conversation_history.append({"role": "user", "content": user_input})

		try:
			response = ollama.chat(
				model=model_name,
				messages=[
					{"role": "system", "content": assistant_instructions},
					*conversation_history,
				],
			)
			assistant_message = response.message.content
			print(f"JARVIS: {assistant_message}")

			# Save JARVIS's answer for the next request too.
			conversation_history.append(
				{"role": "assistant", "content": assistant_message}
			)
		except ollama.ResponseError as error:
			if error.status_code == 404:
				print(
					f"JARVIS: The Ollama model '{model_name}' is unavailable. "
					f"Run: ollama pull {model_name}"
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
