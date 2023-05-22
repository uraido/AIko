""" ==============================================================
AIko.py

Requirements:
- AikoSpeechInterface.py (5.0 or greater) and its requirements
- AikoINIhandler.py

pip install:
- openai

pip3 install:
- pytimedinput   

txt files:
- AIko.txt
- time_out_prompts.txt
- key_openai.txt
- scenarios.txt

Changelog:

080:
- Implemented .ini configuration file.
0801:
- Fixed bug where setting the summarization instruction in the .ini file had no actual effect.
0802:
- Added AIkoINIhandler.py as a dependency.
081:
- Memory slot limit is now configurable.
082:
- Implemented exception handling into generate_gpt_completion() and evaluate_then_summarize()
083:
- Implemented dynamic scenarios
084:
- Further improved completion exception handling by adding the generate_gpt_completion_timeout() function,
which can be useful for circumventing RateLimit errors when the openAI API is overloaded. Default time out
can be configured in the INI.
085:
- Inverted the order that personality and context are placed in the final prompt. Now, context comes first
and personality comes last, to make sure Aiko's personality remains consistent, regardless of context.
086:
- Moved context to the system prompt and personality to the user prompt. This seems to prevent Aiko from
getting 'addicted' to the information stored in the context, since the system prompt has less weight on
the output.
===============================================================================================================================
""" 

# PLEASE set it if making a new build. for logging purposes
build_version = ('Aiko086').upper() 

print(f'{build_version}: Starting...')
print()

if __name__ == '__main__':
  from AikoINIhandler import handle_ini
  handle_ini()

# ----------------- Imports -----------------

import openai                          # gpt3
from AikoSpeechInterface import say    # text to speech function
from AikoSpeechInterface import listen # speech to text function
from datetime import datetime          # for logging
from pytimedinput import timedInput    # input with timeout
from random import randint             # random number generator
from configparser import ConfigParser  # ini file config
from func_timeout import func_timeout, FunctionTimedOut # for handling openAI ratelimit errors

# -------------------------------------------



# ------------- Set variables ---------------

# reads config file
config = ConfigParser()
config.read('AikoPrefs.ini')

# sets variables according to config
breaker = config.get('GENERAL', 'breaker_phrase')
context_slots = config.getint('GENERAL', 'context_slots')
dynamic_scenarios = config.getboolean('GENERAL', 'dynamic_scenarios')
completion_timeout = config.getint('GENERAL', 'completion_timeout')
summarization_instruction = config.get('SUMMARIZATION', 'summary_instruction')
context_character_limit = config.getint('SUMMARIZATION', 'context_character_limit')

# -------------------------------------------



# Set OpenAPI key here
openai.api_key = open("keys/key_openai.txt", "r").read().strip('\n')



# ------------------------------------------- functions -----------------------------------------------

def create_context_list(length : int = context_slots):
  '''
  Returns a limited list of empty strings.
  '''
  new_list = []
  for i in range(length):
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

def generate_gpt_completion(system_message : str, user_message : str):
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

  try:
    request = openai.ChatCompletion.create(
      model = "gpt-3.5-turbo",
      messages = [{"role":"system", "content": system_message},
    {"role":"user", "content": user_message}]
    )

    completion = request.choices[0].message.content
    token_usage = (request.usage.prompt_tokens, request.usage.completion_tokens, request.usage.total_tokens)

    return (completion, token_usage)

  except openai.error.RateLimitError as e:
    print('Aiko.py:')
    print(e)
    print()

    return('', (0,0,0))

def generate_gpt_completion_timeout(system_message : str, user_message : str, timeout : int = completion_timeout):
  """
  Requests a completion under a set timeout in seconds. 
  If the first request fails to return a value under the set time out value, a second request is made.
  Useful for circumventing RateLimit errors when the OpenAI API is overloaded.

  Returns a tuple containing:
  - Str, Completion text
  - Tuple, usage data in tokens.

  """

  try:
    completion_request = func_timeout(timeout, generate_gpt_completion, args = (system_message, user_message))
  except FunctionTimedOut:
    completion_request = generate_gpt_completion(system_message, user_message)
    
  return (completion_request)

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

def create_log():
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
    with open('prompts/AIko.txt', 'r') as aiko_txt:
      for line in aiko_txt:
        log.write(line)
    log.write('\n')
    log.write('\n')
    log.write('---------------END OF "AIko.txt"---------------\n')
    log.write('\n')

  return log_filename

def update_log(log_filepath : str, user_string : str, completion_data : tuple, include_context : bool = False, context_string : str = ''):
  time = datetime.now()
  hour = f'[{time.hour}:{time.minute}:{time.second}]'

  with open(log_filepath, 'a') as log:
    if include_context:
      log.write(f'{hour} Context string: {context_string}\n')
      log.write('\n')
    log.write(f'{hour} Prompt: {user_string} --TOKENS USED: {completion_data[1][0]}\n')
    log.write(f'{hour} Output: {completion_data[0]} --TOKENS USED: {completion_data[1][1]}\n')
    log.write(f'{hour} Total tokens used: {completion_data[1][2]}\n')
    log.write('\n')

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

def update_context(latest_context : str, contexts_list : list):
  '''
  Appends the given context to the given context list and removes the oldest item in the list (index 0).
  Returns a string composed of every item in the context list.
  '''

  contexts_list.pop(0)
  contexts_list.append(latest_context)

  context_string = ''

  for index, context in enumerate(contexts_list, start = 1):
    if context == '':
      continue
    if index == 5:
      context_string += f' {index} (latest) - {context}'
      continue

    context_string += f' {index} - {context}'

  return context_string

def evaluate_then_summarize(
  context : str,
  log : str,
  max_length : int = context_character_limit,
  instruction : str = summarization_instruction,
  ):

  '''
  Summarizes the given string if it is longer than the specified max length.
  Returns the summary as a string OR
  the given string with no changes if the length limit isn't exceeded.
  '''

  if len(context) > max_length:
    summary_request = generate_gpt_completion(instruction, context)
    update_log(log, f'{instruction} {context}', summary_request)

    # returns context without changes if the summary request fails
    if summary_request[0] == '':
      return context

    context = summary_request[0]

  return context
# ----------------------------------- end of functions ------------------------------------------------



if __name__ == "__main__":

  # gets the user's name from config
  username = config.get('GENERAL', 'username')

  # saves the time out prompts into a list

  time_out_prompts = txt_to_list('prompts/time_out_prompts.txt')
    
  # gets aiko.txt and saves it into a string for prompting gpt3

  personality = txt_to_string('prompts/AIko.txt')

  # saves the scenarios into a list

  scenarios = txt_to_list('prompts/scenarios.txt')

  # picks a random scenario and adds it to the personality prompt
  if dynamic_scenarios:
    scenario = scenarios[randint(0, len(scenarios) - 1)]
    personality += scenario

  # creates the log with initial info and saves the logs filename into a variable

  log = create_log()

  # list to save context strings

  context_list = create_context_list()

  # sentence written before main context string in prompt, to make things clear for AIko

  context_start = f'You are Aiko. Here are our last interactions with Aiko:'

  # memory string used to hold context strings

  aikos_memory = 'EMPTY'

  # sets silence breaker times
  min_silence_breaker_time = config.getint('SILENCE_BREAKER', 'min_silence_breaker_time')
  max_silence_breaker_time = config.getint('SILENCE_BREAKER', 'max_silence_breaker_time')

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

    silence_breaker_time = randint(
    min_silence_breaker_time,
    max_silence_breaker_time
    )

    # asks the user for input depending on the chosen input method
  
    user_input, timed_out = get_user_input(silence_breaker_time, username)

    # prepares system message to generate the completion

    system_role_aiko = f"{context_start} {aikos_memory} "


    if timed_out:
      chosen_prompt = randint(0, len(time_out_prompts) - 1)
      user_input = time_out_prompts[chosen_prompt]

    # to give aiko a chance to say her goodbye

    if breaker in user_input.lower():
      user_input += f' ({breaker} means goodbye)'

    # prepares user message to generate the completion

    user_role_aiko = f'{personality} {username}: {user_input} Aiko: '

    # requests the completion and saves it into a string

    aiko_completion_request = generate_gpt_completion_timeout(system_role_aiko, user_role_aiko)

    aiko_completion_text = aiko_completion_request[0]

    print("Aiko: " + aiko_completion_text)

    # voices aiko. set elevenlabs = True if you want to use elevenlabs TTS (needs elevenlabs API key set in key_elevenlabs.txt)
    say(text=aiko_completion_text)

    # updates log
    update_log(log, user_input, aiko_completion_request, True, aikos_memory)

    # prepares latest interaction to be added to the context
    context = f'{username}: {user_input} | Aiko: {aiko_completion_text}'

    # summarizes context if it exceeds the length limit
    context = evaluate_then_summarize(context, log = log)

    # updates context
    aikos_memory = update_context(context, context_list)

    # breaks the loop if the user types the breaker message
    if breaker in user_input.lower():
      break