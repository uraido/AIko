""" ==============================================================
AIko.py

Requirements:
- mpg123 installed and added to PATH var.
- ffmpeg installed and added to PATH var.
- AikoSpeechInterface.py (3.1 or greater)

pip install:
- openai
- gtts
- pydub
- elevenlabslib      (if you want elevenlabs text to speech)
- speechrecognition  (only if you want to speak to her through your mic)
- pyaudio            (speech recognition function dependency)

For libraries you won't use, remember to remove the line which imports them (IE, import pyaudio). If the line does not
exist in this file, you need to remove it from AikoSpeechInterface.py

pip3 install:
- pytimedinput   

txt files:
- AIko.txt
- time_out_prompts.txt
- key_openai.txt
- key_elevenlabs.txt (optional)

Changelog:

060:
- Moved log functionality into create_log(), update_log() and update_log_with_summarization_data() functions
- Renamed create_limited_list() to create_context_list()
- Moved context functionality into update_context_list(), update_context_string() update_context_string_with_summaries() functions
061:
- Add "silence breaker" into the loop, which makes AIko talks when time has passed without interact with her
062:
- Added randomized time out prompts.
- Added variable patience.
- Fixed a bug where the log would not report time out prompts.
063:
- The random timer variable will now reset every time the interaction loop restarts.
- create_context_list() list length is now hardcoded to 5.
- Added txt_to_list() function and updated the time out feature to use it instead of numpy.
- If the user says 'code red', the phrase '(Code red means goodbye) will be added to the prompt to make things clear
for AIko. This is neccessary because if the explanation is included in AIko.txt, AIko keeps mentioning code red all the
time, which is not the desired behavior.

064:
- Added 'user' parameter to update_context_string() function, so AIko can identify who said what.
- The user can write his name in the 'username.txt' file. If this is done, AIko will know the user's name.
- Restructured update_context_string() and update_context_string_with_summaries() for better readability.
- Also added 'user' parameter to get_user_input(), so it nicely prints the username when asking for a prompt.

===============================================================================================================================
""" 



# ----------------- Imports -----------------

import openai                          # gpt3
from AikoSpeechInterface import say    # text to speech function
from AikoSpeechInterface import listen # speech to text function
from datetime import datetime          # for logging
from pytimedinput import timedInput    # input with timeout
from random import randint             # random number generator
import numpy as np

# -------------------------------------------


# PLEASE set it if making a new build. for logging purposes

build_version = ('Aiko064').upper()



# ------------- Set variables ---------------

patience = randint(6, 24)                                         # patience
breaker = "code red"                                              # breaker phrase for aiko's interaction loop
context_start = f'For context, here are our last interactions:'   # prepares aiko's context variables

# -------------------------------------------




# Set OpenAPI key here
openai.api_key = open("key_openai.txt", "r").read().strip('\n')



# ------------------------------------------- functions -----------------------------------------------

def create_context_list():
  new_list = []
  for i in range(5):
    new_list.append('')
  return new_list

def txt_to_string(filename: str):
    """
    Reads text from the specified file and returns it as a string, ignoring any characters
    after a '#' symbol. If the file cannot be opened or read, returns `None`
    and prints an error message.

    Args:
        filename (str): the name of the file to read from

    Returns:
        str or None: the contents of the file as a string, with comment lines removed,
        or `None` if an error occurs
    """
    string = ''
    try:
        with open(filename, "r") as txt_file:
            for line in txt_file:
                line = line.strip()
                if '#' in line:
                    line = line[:line.index('#')]
                string = string + line
    except OSError:
        print(f"Could not open file '{filename}'")
        return None
    return string

def generate_gpt_completion(system_message, user_message):
    """
    Generate a text completion for the given user message, with the help of a system message, using the OpenAI GPT-3.5-Turbo model.

    :param system_message: The system message to provide additional context or guidance to the model.
    :type system_message: str

    :param user_message: The user message to generate a completion for.
    :type user_message: str

    :return: A tuple containing the completion text as a string and usage data for the generated tokens.
        The usage data is a tuple containing three integers: the number of tokens used from the prompt,
        the number of tokens used from the generated completion, and the total number of tokens used.
    :rtype: tuple
    """

    completion_request = openai.ChatCompletion.create(
      model = "gpt-3.5-turbo", 
      messages = [
      {"role":"system", "content": system_message},
      {"role":"user", "content": user_message}]

    )

    completion_text = completion_request.choices[0].message.content
    completion_token_usage_data = (completion_request.usage.prompt_tokens, completion_request.usage.completion_tokens, completion_request.usage.total_tokens)

    return (completion_text, completion_token_usage_data)

def get_user_input(timer : int, user : str):
  """
  Prompts user for input depending on the input method chosen (Text or Microphone)
  and returns the as a string.
  """
  if user_input_method == '1':
    user_input, timed_out = timedInput(f'{user}: ', timeout=timer)

  elif user_input_method == '2':
    user_input = listen('Listening for mic input...')
    timed_out = False
    print(f'User: {user_input}')
    if user_input == None:
      print('No speech detected. Resorting to text...')
      user_input, timed_out = timedInput(f'{user}: ', timeout=timer)
  
  return user_input, timed_out

def create_log(is_summarizing : bool, summary_instruction : str):
  global build_version

  time = datetime.now()
  hour = f'[{time.hour}:{time.minute}:{time.second}]'
  time = time.strftime("%d/%m/%Y %H:%M:%S")
  time = time.replace(' ','_').replace('/','-').replace(':','-')



  # creates the log and reports initial info
  log_filename = r'log/{}.txt'.format(time)

  with open(r'log/{}.txt'.format(time), 'w') as log:
    log.write(f'{hour} AIKO.PY BUILD VERSION: {build_version} \n')
    log.write(f'{hour} AIko.txt: \n')
    with open('AIko.txt', 'r') as aiko_txt:
      for line in aiko_txt:
        log.write(line)
    log.write('\n')
    log.write('\n')
    log.write('---------------END OF "AIko.txt"---------------\n')
    log.write('\n')
    log.write(f'CONTEXT SUMMARIZATION: {is_summarizing}\n')
    if is_summarizing:
      log.write(f"Summarization Prompt: '{summary_instruction}'\n")
    log.write('\n')

  return log_filename

def update_log(log_filepath : str, user_string : str, completion_data : tuple):
  time = datetime.now()
  hour = f'[{time.hour}:{time.minute}:{time.second}]'

  with open(log_filepath, 'a') as log:
    log.write(f'{hour} Prompt: {user_string} --TOKENS USED: {completion_data[1][0]}\n')
    log.write(f'{hour} Output: {completion_data[0]} --TOKENS USED: {completion_data[1][1]}\n')
    log.write(f'{hour} Total tokens used: {completion_data[1][2]}\n')
    log.write('\n')

def update_log_with_summarization_data(log_filepath : str, user_string : str, completion_data : tuple, summaries_list : list, sum_completion_data : tuple):
  time = datetime.now()
  hour = f'[{time.hour}:{time.minute}:{time.second}]'

  with open(log_filepath, 'a') as log:
    log.write(f'{hour} SUMMARY HISTORY:\n')
    for summary in summaries_list:
      if summary != '':
        log.write(f'{hour} Summary: {summary} \n')
    log.write(f'{hour} INTERACTION:\n')
    log.write(f'{hour} Prompt: {user_string} --TOKENS USED: {completion_data[1][0]}\n')
    log.write(f'{hour} Output: {completion_data[0]} --TOKENS USED: {completion_data[1][1]}\n')
    log.write(f'{hour} Total tokens used: {completion_data[1][2]}\n')
    log.write(f'{hour} FINAL USAGE DATA:\n')
    log.write(f'{hour} --TOKENS USED TO SUMMARIZE: {sum_completion_data[1][2]}\n')
    log.write(f'{hour} Total tokens used (Prompt + Output + Summarization): {completion_data[1][2] + sum_completion_data[1][2]}\n')
    log.write('\n')

def update_context_list(list_to_update : list, context : str):
  context_list = list_to_update.copy()
  context_list = context_list[1:]
  context_list.append(context)

  return(context_list)

def update_context_string(user_input_list : list, gpt_output_list, user : str):

  # context string which will be used when requesting completions

  context_string = ''

  # checks whether aikos context lists are empty. if they are, memory update loops wont be run, for better performance.
  # also makes sure the context string keeps the EMPTY keyword when empty

  is_context_empty = False

  if gpt_output_list[4] == '':
    is_context_empty = True

  if is_context_empty:
    context_string = 'EMPTY'
    return context_string

  # adds each context string in the list to the main context string

  for written_index, stored_input in enumerate(user_input_list, start = 1):
    output_list_index = written_index - 1
    if stored_input == '':
      continue
    if written_index == 5:
      context_string += f' {written_index} (latest) - {user} said: {stored_input} | Aiko said: {gpt_output_list[output_list_index]}'
      continue 

    context_string += f' {written_index} - {user} said: {stored_input} | Aiko said: {gpt_output_list[output_list_index]}'

  return(context_string)
  
def update_context_string_with_summaries(summaries_list : list):

  context_string = ''

  is_context_empty = False

  if summaries_list[4] == '':
    is_context_empty = True

  if is_context_empty:
    context_string = 'EMPTY'
    return(context_string)

  for index, summary in enumerate(summaries_list, start = 1):
    if summary == '':
      continue
    if index == 5:
      context_string += f' {index} (latest) - {summary}'
      continue

      context_string += f' {index} - {summary}'

  return(context_string)

def txt_to_list(txt_filename : str):
  """
    Reads a text file with the specified filename and returns a list of its lines.

    Args:
    - txt_filename (str): The name of the text file to read.

    Returns:
    - A list of strings representing each line in the text file, with leading and trailing whitespace removed.
    """
  lines_list = []

  with open(txt_filename, 'r') as txt_file:
    for line in txt_file:
      line = line.strip()
      lines_list.append(line)
  
  return lines_list

# ----------------------------------- end of functions ------------------------------------------------



if __name__ == "__main__":

  # saves the user's name into a string

  username = txt_to_string('username.txt')

  # saves the time out prompts into a list

  time_out_prompts = txt_to_list('time_out_prompts.txt')

  # if set to true (script will ask user when executed) tries to summarize the latest interactions with gpt3 before saving
  # them into her "memory". experimental feature

  context_summarization = False
  summarization_instruction = 'Summarize this shortly without removing core info:'

  set_context_summarization = input("Toggle context summarization? Y/N: ")
  if set_context_summarization.lower() == 'y':
    context_summarization = True
    print('ENABLED CONTEXT SUMMARIZATION.')
    print()
  else:
    print('CONTEXT SUMMARIZATION NOT ENABLED.')
    print()
    
  # gets aiko.txt and saves it into a string for prompting gpt3

  personality = txt_to_string('AIko.txt')

  # creates the log with initial info and saves the logs filename into a variable

  log = create_log(context_summarization, summarization_instruction)

  # lists to save both user inputs and aiko's outputs for context

  inputList, outputList = create_context_list(), create_context_list()

  # if context_summarization is true, then this list will be used instead to save gpt generated summaries

  summary_list = create_context_list()

  # prompts the user to choose a prompting method. defaults to text if input is invalid.

  possible_user_input_methods = ('1', '2')
  user_input_method = input('Choose an input method: 1 - Text 2 - Microphone (PRESS 1 OR 2): ')
  if user_input_method not in possible_user_input_methods:
    user_input_method = '1'
    print('Invalid input method. Defaulting to text.')
    print()

  # ----------------------------------------- aiko's interaction loop --------------------------------------------------

  while True:

    # how long aiko waits for user input before getting impatient

    silence_breaker_time = randint(patience, 60)

    # updates aikos context string

    if context_summarization:
      aikos_memory = update_context_string_with_summaries(summary_list)
    else:
      aikos_memory = update_context_string(inputList, outputList, username)

    print(aikos_memory)

    # asks the user for input depending on the chosen input method
  
    user_input, timed_out = get_user_input(silence_breaker_time, username)

    # prepares system message to generate the completion

    system_role_aiko = f'{personality} {context_start} ### {aikos_memory} ###'


    if timed_out:
      chosen_prompt = randint(0, len(time_out_prompts - 1))
      user_input = time_out_prompts[chosen_prompt]
    if breaker in user_input.lower():
      user_input += ' (Code red means goodbye)'

    # prepares user message to generate the completion

    user_role_aiko = f'{username}: ### {user_input} ### Aiko: '

    # requests the completion and saves it into a string

    aiko_completion_request = generate_gpt_completion(system_role_aiko, user_role_aiko)

    aiko_completion_text = aiko_completion_request[0]

    print("Aiko: " + aiko_completion_text)
    print()

    # voices aiko. set elevenlabs = True if you want to use elevenlabs TTS (needs elevenlabs API key set in key_elevenlabs.txt)
    say(text=aiko_completion_text, elevenlabs = False, audiodevice = "2")

    # updates aiko's context lists based on the latest interaction

    if context_summarization:
      user_role_sum = f'### {username} says: {user_input} Aiko says: {aiko_completion_text} ###'

      summary_completion_request = generate_gpt_completion(summarization_instruction, user_role_sum)
      summary_completion_text = summary_completion_request[0]

      summary_list = update_context_list(summary_list, summary_completion_text)

    else:
      inputList = update_context_list(inputList, user_input)
      outputList = update_context_list(outputList, aiko_completion_text)

    # updates log

    if context_summarization:
      update_log_with_summarization_data(log, user_input, aiko_completion_request, summary_list, summary_completion_request)
    else:
      update_log(log, user_input, aiko_completion_request)

    # breaks the loop

    if breaker in user_input.lower():
      break