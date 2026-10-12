# Gemma 4 Local Coding Assistant

This is a Python script I made that lets me chat with Gemma 4 locally through Ollama right in my terminal. You can upload a file to it and it'll either answer questions about the code or edit the file for you, depending on what you ask.

Everything runs on your own machine, so no API keys and nothing gets sent anywhere.

**This is version 1.** It's pretty basic right now but I'm adding more soon (see [Coming soon](#coming-soon)).

## What you need

- Python 3.10 or newer (the script uses `match`/`case`)
- [Ollama](https://ollama.com) installed and running
- The Gemma 4 model pulled:
  ```
  ollama pull gemma4
  ```
- The Ollama Python package:
  ```
  pip install ollama
  ```

## Setup

I run it in a virtual environment so the packages stay separate:

```
python3 -m venv .venv-1
source .venv-1/bin/activate
pip install ollama
```

## Running it

```
python gemma-4.py
```

Then just type at the `You:` prompt. Type `exit` or `quit` to close it.

## How to use it

### Normal chat
Just type a message with no keyword and it works like a regular chatbot. It keeps the whole conversation in history so it remembers what you talked about.

### Uploading a file
Put `[upload]` in front of the full file path, then whatever you want it to do:

```
[upload]/Users/you/Desktop/LLMS/test.py what does this file do
```

```
[upload]/Users/you/Desktop/LLMS/test.py remove the derivative part of the calculator
```

The AI decides on its own whether you want an explanation or an edit:
- If you ask a question, it just answers.
- If you ask for a change, it rewrites the file and the script saves it straight back to the file you uploaded.

### Follow up edits
After uploading once, you can keep asking for changes without the keyword:

```
now add an exponent calculator to the same file
```

It'll write to the last file you uploaded. It works off its own last version from the chat history though, so if you edit the file yourself in between, `[upload]` it again so it sees your changes.

## Supported file types

The file path has to end in one of these so the script knows where the path stops:

`.json` `.js` `.py` `.java` `.cpp` `.css` `.c` `.html` `.ts` `.txt` `.md`

To add more, just add them to `supported_file_types` at the top of the script. Put longer ones before shorter ones that start the same (like `.json` before `.js`).

## Settings

At the top of `gemma-4.py`:

- `SYSTEM_PROMPT` controls how the AI acts in general. It's set up to follow KISS, YAGNI, and DRY so it keeps the code simple and only changes what you asked for.
- `UPLOAD_PROMT` has the instructions for when a file is uploaded, including the format it uses for edits.
- `is_thinking_on` turns Gemma's thinking on or off. On is smarter but there's a pause before it starts answering. Off is faster.

## How the editing works

When the AI wants to edit a file, it puts the new code between tags like this:

```
[start-file]/path/to/file.py[end-file]
[start-code]
...the whole file...
[end-code]
```

The script looks for those tags after the reply finishes and writes the code to the file you uploaded. If there are no tags, nothing gets written.

## Heads up

- **It overwrites your file with no backup.** Keep your project in git (or make a copy) so you can undo a bad edit.
- If you ask something vague like "this part seems off," it might take that as an edit request. Say "don't change anything" if you just want an explanation.
- Long chats get slower since the whole history gets sent every message. Restart the script to clear it.
- Run your test files in a separate terminal so you don't stop the assistant.

## Coming soon

- **File creation:** right now it can only edit files you upload. Next version it'll be able to make new files too.
- **Context saving:** right now the chat history is gone when you close the script. I'm adding a way to save it so you can pick up where you left off.