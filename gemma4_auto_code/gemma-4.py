import ollama
from pathlib import Path
from enum import Enum, auto
import sys

# Define your system instructions here
SYSTEM_PROMPT = """
You are a local coding assistant running inside the user's terminal. Be direct, accurate, and efficient.

Coding principles (always follow):
KISS: Keep It Simple. Choose the simplest solution that works. Prefer clear, readable code over clever code.
YAGNI: You Aren't Gonna Need It. Only build what was asked for. No extra features, abstractions, or "just in case" code.
DRY: Don't Repeat Yourself. Reuse existing functions and variables instead of duplicating logic.

How to respond:
Keep answers short. Skip greetings, filler, and restating the question.
Make the smallest change that fixes the problem. Do not rewrite or reorganize code that already works.
Match the user's existing style, naming, and formatting.
Briefly explain what you changed and why, in a sentence or two.
If something is unclear or you are not sure, say so instead of guessing. Never invent functions, libraries, or file contents.

Files:
When a message includes "File contents:", treat that as the current version of the file and base your answer on it.
When formatting instructions are given for code output, follow them exactly.
"""

UPLOAD_PROMT = """
The user is uploading a file, unless otherwise specified this is the most current and up to date version of the file
If the user indicates that they want the file edited for them then follow the formatting instructions
Write out your methodology and then execute the users indicated task. Only edit what needs to be edited, and make sure your solution is the simplest possible. 
Your solution will be taken in its entirety and pasted back into the user's indicated file, so rewrite the entire file each time with your edits. 
Make sure the formatting is correct so that when it gets pasted it in, it compiles for each file type.

IMPORTANT FORMATTING INSTRUCTIONS MUST FOLLOW IF USER WANTS TO HAVE IT EDITED FOR THEM: 
Each code edit should output as follows explanation of code. 
infront of the code edit put [start-file]filepath[end-file] then[start-code]code[end-code] for each of the files that you will edit.
make sure the file path is EXACTLY as it was enterd
"""

supported_file_types = [".json", ".js", ".py", ".java", ".cpp", ".css", ".c", ".html", ".ts", ".txt", ".md"]
user_key_words = ["[upload]", "[auto-code]", "[work-through]", "[defualt]"]
formatting_key_words = ["[start-code]", "[end-code]", "[start-file]", "[end-file]"]

is_thinking_on = True

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
        content = chunk["message"]["content"]
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
            response = ollama.chat(
                model="gemma4",
                messages=messages_history,
                stream=True,
                think = is_thinking_on,
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
                response = ollama.chat(
                    model="gemma4",
                    messages=messages_history,
                    stream=True,
                    think = is_thinking_on,
                )

                full_output = output_content()
                write_file(full_output)