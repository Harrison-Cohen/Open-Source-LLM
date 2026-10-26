from openai import OpenAI, BadRequestError
from pathlib import Path
from enum import Enum, auto
from datetime import datetime
import json
import re
import shutil
import sys
import urllib.request

SERVER_URL = "http://localhost:8080"
client = OpenAI(base_url=f"{SERVER_URL}/v1", api_key="none")

"""
   cd ~/Desktop/LLMS/llama.cpp
   ./build/bin/llama-server -hf deeonline/K2-Horizon-7B-GGUF:Q5_K_M -c 20000 --jinja
"""
SYSTEM_PROMPT = """
You are K2 Horizon 7B, an open-source model made by IFM, running locally as a coding assistant inside the user's terminal. Be direct, accurate, and efficient.

Coding principles (always follow):
KISS: Keep It Simple. Choose the simplest solution that works. Prefer clear, readable code over clever code.
YAGNI: You Aren't Gonna Need It. Only build what was asked for. No extra features, abstractions, or "just in case" code.
DRY: Don't Repeat Yourself. Reuse existing functions and variables instead of duplicating logic.

How to respond:
Never assume anything unless told to
Always ask the user questions if anything is unlcear or needs to be verified
Keep answers short. Skip greetings, filler, and restating the question.
Make the smallest change that fixes the problem. Do not rewrite or reorganize code that already works.
Match the user's existing style, naming, and formatting.
If something is unclear or you are not sure, say so instead of guessing. Never invent functions, libraries, or file contents.

Editing files:
Put [start-file]filepath[end-file] then [start-code]code[end-code] at the very end of your response.
Example of the correct format:
[start-file]/Users/you/project/example.py[end-file]
[start-code]
print("hello")
[end-code]
Only edit a file when the user asks for a change. If the user asks a question, just answer it.
When you edit a file, first explain what you changed and why in a sentence or two.
Then at the very end of your response, write out the entire updated file using the formatting instructions.

IMPORTANT FORMATTING INSTRUCTIONS MUST FOLLOW:
Put [start-file]filepath[end-file] then [start-code]code[end-code] at the very end of your response.
The filepath must be the full path exactly as the user typed it, starting with /.
The code must be the entire file, not just the lines you changed.
Only use these tags once, at the end. Never mention or write these tags anywhere else in your response.
Do not put markdown code fences inside the tags.
You have no tools, only the actions below. Never output tool calls or <ifm|...> tags.

Example of the correct format:
[start-file]/Users/you/project/example.py[end-file]
[start-code]
print("hello")
[end-code]

Actions:
Write one action per line, each line starting with the keyword. Put them before any [start-file] block, at the end of your response. Always use full paths starting with /.
[mkdir] /full/path/to/new/folder
[read] /full/path/to/file
[list] /full/path/to/folder
[delete] /full/path
[move] /old/path -> /new/path
[mkdir] creates a folder and any missing parent folders. [read] gives you the contents of a file. [list] gives you the names inside a folder. [delete] removes a file or folder, the user is asked to confirm. [move] moves or renames.
To create a file inside a new folder, put the [mkdir] line first, then the [start-file] and [start-code] block.
Example of creating a folder and a file inside it:
Creating the folder and the file.
[mkdir] /Users/you/project/utils
[start-file]/Users/you/project/utils/helper.py[end-file]
[start-code]
print("hello")
[end-code]
Only use an action when the user asks for it or the task needs it. Never start a line with an action keyword in any other situation.
After your actions run you get a message with the results. Use it to continue.

Errors:
If an action or an edit fails you get a message with the error. Read it, fix the mistake and try again. Do not repeat the same mistake.
"""

UPLOAD_PROMT = """
The user is uploading a file, unless otherwise specified this is the most current and up to date version of the file.
If the user wants the file edited, follow the formatting instructions from your system prompt.
"""

ACTION_RESULTS_PROMPT = """
These are the results of the actions you just ran, they are not a message from the user.
Use them to continue the task. If an action had an error, fix it and try again.
"""

SUMMARY_PROMPT = """
The chat history is almost full. Summarize this whole conversation so it can be continued later from the summary alone.
Include what the user is working on, the full path of every file and folder involved, what has been created or changed so far, decisions that were made, and what is still left to do.
Keep it short and factual. Do not use any tags or actions in the summary.
"""

SUMMARY_RESUME_PROMPT = """
This is a summary of our earlier conversation, continue from it.
Files may have changed since then, read a file again before editing it if you are not sure.

"""

supported_file_types = [".json", ".js", ".py", ".java", ".cpp", ".css", ".c", ".html", ".ts", ".txt", ".md", ".rs"]
user_key_words = ["[upload]", "[auto-code]", "[work-through]", "[defualt]", "[mkdir]"]
formatting_key_words = ["[start-code]", "[end-code]", "[start-file]", "[end-file]"]

#current best model for 16 gig systems
MODEL_NAME = "k2-horizon"

#how many times in a row the AI can act and get the results back before it has to stop
MAX_ROUNDS = 5

#when the history is this full of the server's context size it gets summarized and saved to a file
SUMMARY_THRESHOLD = 0.8
HISTORY_FOLDER = Path(__file__).resolve().parent / "history"

class State(Enum):
    UPLOAD = auto()
    DEFAULT = auto()
    MAKE_DIR = auto()

# Initialize the chat history list with your system instructions
messages_history = [{"role": "system", "content": SYSTEM_PROMPT}]

def get_file_from_filepath(input):

    input = input.strip()

    #gives last index of the file keyword
    for key_word in user_key_words:
        if(input.find(key_word) != -1):
            start_index = input.find(key_word) + len(key_word)
            break

    #handles case if user puts in space in front of filepath
    if(input == user_key_words[0]):
        return None, "No filepath provided"


    #find index of the end of the filepath with supported filepath types
    for filetype in supported_file_types:
        end_index = input.find(filetype, start_index)
        if(end_index != -1):
            end_index += len(filetype)
            break

    #if no end of filepath found then throw an error 
    if(end_index == -1):
        return None, "Error could not find supported file type, check list of suppoted types and try again"

    file_path_string = input[start_index:end_index].strip()


    return read_file(file_path_string)

def read_file(file_path_string):

    file_path = Path(file_path_string)

    #handles all errors
    try:
        file_contents = file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"File not found: {file_path_string}"
    except IsADirectoryError:
        return None, f"That path is a folder, not a file: {file_path_string}"
    except PermissionError:
        return None, f"No permission to read: {file_path_string}"
    except UnicodeDecodeError:
        return None, f"Can't read as text (binary file?): {file_path_string}"

    return file_contents, None

def find_current_state(input):
    if input.lower() in ['exit', 'quit']:
            print("Goodbye!")
            sys.exit()
    elif user_key_words[0] in input:
        return State.UPLOAD
    elif user_key_words[4] in input:
        return State.MAKE_DIR
    else:
        return State.DEFAULT

def write_file(output):
    #only keep the last file block in case the AI mentions the markers earlier
    last_start_index = output.rfind(formatting_key_words[2])
    if(last_start_index != -1):
        output = output[last_start_index:]

    while(True):
        if(output.find(formatting_key_words[2]) != -1):
            #gets the filepath from AI output for each file
            file_start_index = output.find(formatting_key_words[2]) + len(formatting_key_words[2])
            file_end_index = output.find(formatting_key_words[3])

            #gets code index for each file
            code_start_index = output.find(formatting_key_words[0]) + len(formatting_key_words[0])
            code_end_index = output.find(formatting_key_words[1])

            file_path_string = output[file_start_index:file_end_index].strip()
            code_string = output[code_start_index:code_end_index]

            #without code there is nothing to write, don't overwrite the file with junk
            if(output.find(formatting_key_words[0]) == -1):
                return None, f"No {formatting_key_words[0]} found for {file_path_string}, nothing was written"

            file_path = Path(file_path_string)

            try:
                file_path.write_text(code_string)
            except FileNotFoundError:
                return None, f"Folder not found for: {file_path_string}, create it first with [mkdir]"
            except IsADirectoryError:
                return None, f"That path is a folder, not a file: {file_path_string}"
            except PermissionError:
                return None, f"No permission to write: {file_path_string}"

            print(f"Wrote file: {file_path_string}")

            output = output[(code_end_index + len(formatting_key_words[1])):]
        else:
            break

    return None, None

def output_content(response):
    # Capture the full assistant response so we can save it to history
    full_assistant_response = ""
    total_tokens = None
    print("AI: ", end="")

    # Loop through the chunks as they arrive from the GPU
    for chunk in response:
        #the server sends the token count of the whole history at the end
        if(chunk.usage):
            total_tokens = chunk.usage.total_tokens

        #that last chunk has no text in it
        if(not chunk.choices):
            continue

        delta = chunk.choices[0].delta
        thinking = getattr(delta, "reasoning_content", None)
        if(thinking):
            print(thinking, end="", flush=True)
        content = delta.content or ""
        print(content, end="", flush=True)
        full_assistant_response += content
    print()  # Print a final new line when done

    # Append the assistant's complete response back to the history
    messages_history.append({"role": "assistant", "content": full_assistant_response})

    return full_assistant_response, total_tokens

def create_directory(directory_path_string):

    directory_path = Path(directory_path_string)

    try:
        directory_path.mkdir(parents=True)
    except FileExistsError:
        return None, f"Directory already exists: {directory_path_string}"
    except PermissionError:
        return None, f"No permission to create directory: {directory_path_string}"
    except OSError as e:
        return None, f"Error creating directory: {directory_path_string} ({e})"

    return None, None

def list_directory(directory_path_string):

    directory_path = Path(directory_path_string)

    try:
        #folders get a / on the end so the AI can tell them apart from files
        names = sorted(f"{item.name}/" if item.is_dir() else item.name for item in directory_path.iterdir())
    except FileNotFoundError:
        return None, f"Folder not found: {directory_path_string}"
    except NotADirectoryError:
        return None, f"That path is a file, not a folder: {directory_path_string}"
    except PermissionError:
        return None, f"No permission to read: {directory_path_string}"

    if(not names):
        return "(empty folder)", None

    return "\n".join(names), None

def delete_path(path_string):

    path = Path(path_string)

    if(not path.exists()):
        return None, f"Path not found: {path_string}"

    #deleting can't be undone so always ask first
    if(path.is_dir()):
        answer = input(f"Delete folder and everything inside it: {path_string} (y/n)? ")
    else:
        answer = input(f"Delete file: {path_string} (y/n)? ")

    if(answer.strip().lower() != "y"):
        return None, f"User declined to delete: {path_string}"

    try:
        if(path.is_dir()):
            shutil.rmtree(path)
        else:
            path.unlink()
    except PermissionError:
        return None, f"No permission to delete: {path_string}"
    except OSError as e:
        return None, f"Error deleting: {path_string} ({e})"

    return None, None

def move_path(move_string):

    #format is: old path -> new path
    paths = move_string.split("->")
    if(len(paths) != 2):
        return None, "Move needs two paths, like: [move] /old/path -> /new/path"

    old_path_string = paths[0].strip()
    new_path_string = paths[1].strip()

    try:
        shutil.move(old_path_string, new_path_string)
    except FileNotFoundError:
        return None, f"Path not found: {old_path_string}, or the folder for {new_path_string} does not exist"
    except PermissionError:
        return None, f"No permission to move: {old_path_string}"
    except OSError as e:
        return None, f"Error moving: {old_path_string} ({e})"

    return None, None

#one line actions the AI can put in its response, each takes the rest of the line and returns (result, error)
ai_actions = {
    user_key_words[4]: create_directory,
    "[read]": read_file,
    "[list]": list_directory,
    "[delete]": delete_path,
    "[move]": move_path,
}

def run_actions(output):

    #results and errors get sent back to the AI so it can keep going or fix its mistakes
    feedback = ""

    #the one line actions come before the file block, the model sometimes leaks its own <ifm|...> tags around them
    action_text = re.sub(r"</?ifm\|[^>]*>", "\n", output.split(formatting_key_words[2])[0])

    #the model also sometimes repeats an action line, so each one only runs once
    action_lines = dict.fromkeys(line.strip() for line in action_text.splitlines())

    for line in action_lines:
        for key_word, action in ai_actions.items():
            if(line.startswith(key_word)):
                result, error = action(line[len(key_word):].strip())
                if(error):
                    print(error)
                    feedback += f"{line}\nError: {error}\n\n"
                else:
                    print(f"Done: {line}")
                    #only read and list give the AI something back
                    if(result):
                        feedback += f"{line}\n{result}\n\n"
                break

    _, error = write_file(output)
    if(error):
        print(error)
        feedback += f"File edit\nError: {error}\n\n"

    return feedback

def ask_model():

    # Pass the entire running history to Ollama
    try:
        return client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages_history,
            stream=True,
            stream_options={"include_usage": True},
        )
    except BadRequestError as e:
        print(f"The server rejected the request, the chat history is probably too long for the context size ({e})")
        return None

def get_context_size():

    #asks the server how many tokens it can hold at once
    try:
        with urllib.request.urlopen(f"{SERVER_URL}/props", timeout=5) as props:
            return json.load(props)["default_generation_settings"]["n_ctx"]
    except (OSError, KeyError, ValueError):
        return None

def save_history(summary, transcript):

    file_path = HISTORY_FOLDER / f"history_{datetime.now():%Y-%m-%d_%H-%M-%S}.md"

    #summary first so it can be used to pick the conversation back up, then every message word for word
    file_text = f"# Summary\n\n{summary}\n\n# Full transcript\n"
    for message in transcript:
        speaker = "AI" if message["role"] == "assistant" else "User"
        file_text += f"\n## {speaker}\n\n{message['content']}\n"

    try:
        HISTORY_FOLDER.mkdir(exist_ok=True)
        file_path.write_text(file_text, encoding="utf-8")
    except OSError as e:
        return None, f"Could not save the history to {file_path} ({e})"

    return file_path, None

def summarize_history():

    print("\nThe chat history is almost full, summarizing it")

    #copy so the history can be put back exactly as it was if the summary fails
    saved_history = messages_history[:]

    messages_history.append({"role": "user", "content": SUMMARY_PROMPT})
    response = ask_model()
    if(not response):
        messages_history[:] = saved_history
        return

    summary, _ = output_content(response)
    summary = re.sub(r"</?ifm\|[^>]*>", " ", summary).strip()
    if(not summary):
        print("The AI gave an empty summary, keeping the full history")
        messages_history[:] = saved_history
        return

    #the system prompt is the same every time so it is not part of the saved transcript
    file_path, error = save_history(summary, saved_history[1:])
    if(error):
        print(error)
    else:
        print(f"Saved the history to: {file_path}")

    #new history is the system prompt and the summary, the reply keeps user and AI turns alternating
    messages_history[:] = [
        saved_history[0],
        {"role": "user", "content": SUMMARY_RESUME_PROMPT + summary},
        {"role": "assistant", "content": "Understood, I will continue from that summary."},
    ]
    print("Started a new chat history from the summary")

def send_to_ai(content):

    # Append the user's new message to the running history
    messages_history.append({"role": "user", "content": content})

    total_tokens = None

    for round_number in range(MAX_ROUNDS):

        response = ask_model()
        if(not response):
            #the history was too long to even send so it can't be summarized either
            total_tokens = None
            break

        full_output, total_tokens = output_content(response)
        feedback = run_actions(full_output)

        #nothing to report back so the AI is done
        if(not feedback):
            break

        if(round_number == MAX_ROUNDS - 1):
            print(f"Stopped after {MAX_ROUNDS} rounds of actions")
            break

        print("Sending action results back to the AI")
        messages_history.append({"role": "user", "content": ACTION_RESULTS_PROMPT + feedback})

    #when the history is close to the context size, summarize it and start a new one from the summary
    context_size = get_context_size()
    if(total_tokens and context_size and total_tokens > context_size * SUMMARY_THRESHOLD):
        summarize_history()

while True:

    user_input_prompt = input("\nYou: ")

    file_as_text = None

     # Skip empty inputs
    if not user_input_prompt.strip():
        continue

    current_state = find_current_state(user_input_prompt)

    match current_state:
        # No special charaters used, revert to normal prompting
        case State.DEFAULT:
            content = user_input_prompt

            send_to_ai(content)

        # Uploads relevent file
        case State.UPLOAD:
            file_as_text, error = get_file_from_filepath(user_input_prompt)
            if (error):
                print(error)
                continue
            elif(file_as_text):
                user_input_prompt += f"\n\nFile contents:\n{file_as_text}"

                content = user_input_prompt
                content += "\n\n" + UPLOAD_PROMT

                send_to_ai(content)
        # Creates a new directory
        case State.MAKE_DIR:
            #strip off the [mkdir] keyword
            directory_path_string = user_input_prompt.replace(user_key_words[4], "").strip()

            #strip off any leading slash
            if(directory_path_string.startswith("/")):
                directory_path_string = directory_path_string[1:]

            _, error = create_directory(directory_path_string)
            if(error):
                print(error)
                continue

            print(f"Created directory: {directory_path_string}")
            continue