from openai import OpenAI
from pathlib import Path
from enum import Enum, auto
import sys

client = OpenAI(base_url="http://localhost:8080/v1", api_key="none")

"""
   cd ~/Desktop/LLMS/llama.cpp
   ./build/bin/llama-server -hf deeonline/K2-Horizon-7B-GGUF:Q5_K_M -c 8192
"""

# Define your system instructions here
SYSTEM_PROMPT = """
You are K2 Horizon 7B, an open-source model made by IFM, running locally as a coding assistant inside the user's terminal. Be direct, accurate, and efficient.

Coding principles (always follow):
KISS: Keep It Simple. Choose the simplest solution that works. Prefer clear, readable code over clever code.
YAGNI: You Aren't Gonna Need It. Only build what was asked for. No extra features, abstractions, or "just in case" code.
DRY: Don't Repeat Yourself. Reuse existing functions and variables instead of duplicating logic.

How to respond:
Keep answers short. Skip greetings, filler, and restating the question.
Make the smallest change that fixes the problem. Do not rewrite or reorganize code that already works.
Match the user's existing style, naming, and formatting.
If something is unclear or you are not sure, say so instead of guessing. Never invent functions, libraries, or file contents.

Editing files:
Only edit a file when the user asks for a change. If the user asks a question, just answer it.
When you edit a file, first explain what you changed and why in a sentence or two.
Then at the very end of your response, write out the entire updated file using the formatting instructions below.

IMPORTANT FORMATTING INSTRUCTIONS MUST FOLLOW:
Put [start-file]filepath[end-file] then [start-code]code[end-code] at the very end of your response.
The filepath must be the full path exactly as the user typed it, starting with /.
The code must be the entire file, not just the lines you changed.
Only use these tags once, at the end. Never mention or write these tags anywhere else in your response.
Do not put markdown code fences inside the tags.
You have no tools. Never output tool calls or <ifm|...> tags.

Example of the correct format:
[start-file]/Users/you/project/example.py[end-file]
[start-code]
print("hello")
[end-code]
"""

UPLOAD_PROMT = """
The user is uploading a file, unless otherwise specified this is the most current and up to date version of the file.
If the user wants the file edited, follow the formatting instructions from your system prompt.
"""

supported_file_types = [".json", ".js", ".py", ".java", ".cpp", ".css", ".c", ".html", ".ts", ".txt", ".md"]
user_key_words = ["[upload]", "[auto-code]", "[work-through]", "[defualt]"]
formatting_key_words = ["[start-code]", "[end-code]", "[start-file]", "[end-file]"]

#current best model for 16 gig systems 
MODEL_NAME = "k2-horizon"

class State(Enum):
    UPLOAD = auto()
    DEFAULT = auto()

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

            file_path = Path(file_path_string)

            try:
                file_path.write_text(code_string)
            except FileNotFoundError:
                return None, f"File not found: {file_path_string}"
            except IsADirectoryError:
                return None, f"That path is a folder, not a file: {file_path_string}"
            except PermissionError:
                return None, f"No permission to write: {file_path_string}"

            output = output[(code_end_index + len(formatting_key_words[1])):]
        else:
            break

def output_content():
    # Capture the full assistant response so we can save it to history
    full_assistant_response = ""
    print("AI: ", end="")
    
    # Loop through the chunks as they arrive from the GPU
    for chunk in response:
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

    return full_assistant_response



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

            # Append the user's new message to the running history
            messages_history.append({"role": "user", "content": content})
            
            # Pass the entire running history to Ollama
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages_history,
                stream=True,
            )

            full_output = output_content()
            write_file(full_output)
            
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

                # Append the user's new message to the running history
                messages_history.append({"role": "user", "content": content})
                
                # Pass the entire running history to Ollama
                response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages_history,
                stream=True,
                )

                full_output = output_content()
                write_file(full_output)