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

100alpha:
- Interactions are now fully handed by the new AIko class.
- txt_to_string() function now returns an empty string instead of None when an error occurs.
- Many dynamic features, such as silence breaker and scenarios have been temporalily removed. They need to be
adapted to work with the latest changes before they can be reimplemented.

101alpha:
- Reimplemented scenarios.
- Implemented side prompts, which can be added using the add_side_prompt AIko method.
- Using non timeout version of generate_gpt_completion function for now, since the timeout version is throwing
errors.

102alpha:
- AIko.interact() method now has a use_system_role parameter.
- AIko.interact()'s username parameter is now optional.
===============================================================================================================================
""" 

# PLEASE set it if making a new build. for logging purposes
build_version = ('Aiko102alpha').upper() 

print(f'{build_version}: Starting...')
print()

if __name__ == '__main__':
  from AikoINIhandler import handle_ini
  handle_ini()

# ----------------- Imports -----------------

import openai                          # gpt3
from VoiceLink import say    # text to speech function
from datetime import datetime          # for logging
from pytimedinput import timedInput    # input with timeout
from random import choice              # random
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
completion_timeout = config.getint('GENERAL', 'completion_timeout')

# unused
dynamic_scenarios = config.getboolean('GENERAL', 'dynamic_scenarios')
summarization_instruction = config.get('SUMMARIZATION', 'summary_instruction')
context_character_limit = config.getint('SUMMARIZATION', 'context_character_limit')
include_context_in_log = config.getboolean('LOGGING', 'include_context')

# -------------------------------------------

# Set OpenAPI key here
openai.api_key = open("keys/key_openai.txt", "r").read().strip('\n')

# for keeping track of token usage
session_token_usage = 0

# ------------------------------------------- functions -----------------------------------------------

def create_context_list(dummy_object : "any" = '', length : int = context_slots):
  '''
  Returns a limited list of empty strings.
  '''
  new_list = []
  for i in range(length):
    new_list.append(dummy_object)
  return new_list

def txt_to_string(filename: str):
    """
    Reads text from the specified file and returns it as a string, ignoring any characters
    after a '#' symbol. If the file cannot be opened or read, returns `None`
    and prints an error message.

    Args:
        filename (str): the name of the file to read from

    Returns:
        str: the contents of the file as a string, with comment lines removed
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
    return string

def generate_gpt_completion(messages : list):
  """
  Generates a GPT completion by providing a list of messages.

  Args:
      messages (list): A list of dictionaries representing the messages in the conversation.
          Each dictionary should follow the format: {"role": <role>, "content": <content>}.
          - <role> (str): The role of the message, such as "user" or "assistant".
          - <content> (str): The content of the message.

  Returns:
      tuple: A tuple containing the generated completion and token usage information.
          - completion (str): The generated completion text.
          - token_usage (tuple): A tuple of token usage information.
              - prompt_tokens (int): The number of tokens used in the prompt.
              - completion_tokens (int): The number of tokens used in the completion.
              - total_tokens (int): The total number of tokens used.
  """

  try:
    request = openai.ChatCompletion.create(
      model = "gpt-3.5-turbo",
      messages = messages
      )

    completion = request.choices[0].message.content
    token_usage = (request.usage.prompt_tokens, request.usage.completion_tokens, request.usage.total_tokens)

    return (completion, token_usage)

  except openai.error.RateLimitError as e:
    print('Aiko.py:')
    print(e)
    print()

    return('', (0,0,0))

def generate_gpt_completion_timeout(messages : list, timeout : int = completion_timeout):
  """
  Requests a completion under a set timeout in seconds. 
  If the first request fails to return a value under the set time out value, a second request is made.
  Useful for circumventing RateLimit errors when the OpenAI API is overloaded.

  Returns a tuple containing:
  - Str, Completion text
  - Tuple, usage data in tokens.

  """

  try:
    completion_request = func_timeout(timeout, generate_gpt_completion, args = (messages))
  except FunctionTimedOut:
    completion_request = generate_gpt_completion(messages)
    
  return (completion_request)

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

class AIko:
  """
    A class that can be used for interacting with custom made AI characters.

    Attributes:
        character_name (str): The name of the AI character.
        personality_file (str): The filename of the personality file.
        __personality__ (str): The personality text loaded from the personality file.
        __log__ (str): The filename of the log file.
        __context__ (list): A list of user and assistant messages representing the conversation context.

    Methods:
        __init__(self, character_name: str, personality_filename: str):
            Initializes an instance of the AIko class.
        
        __create_log__(self):
            Creates a log file and reports initial information.
        
        __update_log__(self, user_string: str, completion_data: tuple):
            Updates the log file with the user's input and the generated output.
        
        interact(self, username: str, message: str):
            Interacts with the AI character by providing a username and a message.
    """

  def __init__(self, character_name : str, personality_filename : str, scenario : str = ''):
    """
    Initializes an instance of the AIko class.

    Args:
        character_name (str): The name of the AI character.
        personality_filename (str): The filename of the personality file.
    """
    self.character_name = character_name
    self.personality_file = personality_filename
    self.scenario = scenario
    self.__personality__ = txt_to_string(personality_filename)
    self.__log__ = self.__create_log__()
    self.__context__ = create_context_list(('', ''))
    self.__side_prompts__ = create_context_list()

  def __create_log__(self):
    """
    Creates a log file and reports initial information.

    Returns:
        log_filename (str): The filename of the created log file.
    """
    global build_version

    time = datetime.now()
    hour = f'[{time.hour}:{time.minute}:{time.second}]'
    time = time.strftime("%d/%m/%Y %H:%M:%S")
    time = time.replace(' ','_').replace('/','-').replace(':','-')

    log_filename = r'log/{}.txt'.format(time)

    with open(r'log/{}.txt'.format(time), 'w') as log:
      log.write(f'{hour} AIKO.PY BUILD VERSION: {build_version} \n')
      log.write(f'{hour} {self.personality_file}: \n')
      with open(self.personality_file, 'r') as aiko_txt:
        for line in aiko_txt:
          log.write(line)
      log.write('\n')
      log.write('\n')
      log.write(f'---------------END OF "{self.personality_file}"---------------\n')
      log.write('\n')

    return log_filename

  def __update_log__(self, user_string : str, completion_data : tuple):
    """
    Updates the log file with the user's input and the generated output.

    Args:
        user_string (str): The user's input message.
        completion_data (tuple): A tuple containing the generated output and token usage information.
    """
    global session_token_usage

    time = datetime.now()
    hour = f'[{time.hour}:{time.minute}:{time.second}]'

    session_token_usage += completion_data[1][2]

    with open(self.__log__, 'a') as log:
      log.write(f'{hour} Prompt: {user_string} --TOKENS USED: {completion_data[1][0]}\n')
      log.write(f'{hour} Output: {completion_data[0]} --TOKENS USED: {completion_data[1][1]}\n')
      log.write(f'{hour} Total tokens used: {completion_data[1][2]}\n')
      log.write('\n')
      log.write(f'{hour} Tokens used this session: {session_token_usage}\n')
      log.write('\n')

  def interact(self, message : str, username : str = 'User', use_system_role : bool = False):
    """
    Interacts with the AI character by providing a username and a message.

    Args:
        message (str): The message sent by the user.
        username (str): The username.
        use_system_role (bool): Whether to use the system role instead of the user role when prompting the user's
        message.
    """
    messages = [{"role":"system", "content": self.__personality__},]
    if self.scenario != '':
      messages.append({"role":"system", "content": self.scenario})

    # parses side prompts and adds them to the messages
    if self.__side_prompts__[-1] != '':
      for side_prompt in self.__side_prompts__:
        if side_prompt != '':
          messages.append({"role":"system", "content": side_prompt})

    # parses context list and adds interactions to the messages
    if self.__context__[-1] != ('', ''):
      for context in self.__context__:
        if context != ('', ''):
          messages.append({"role":"user", "content": context[0]})
          messages.append({"role":"assistant", "content": context[1]})

    # adds user prompt to the messages
    if use_system_role:
      messages.append({"role":"system", "content": message})
    else:
      messages.append({"role":"user", "content": f'{username}: {message}'})

    # requests completion
    completion = generate_gpt_completion(messages)
    print(completion[0])

    # parses completion to be fed to text to speech
    #if f'{self.character_name}:' in completion[0][:len(self.character_name) + 2]:
      #say(completion[0][len(self.character_name) + 1:])
    # otherwise just voices it if no parsing is needed
    #else:
      #say(completion[0])

    # updates context list with latest interaction
    self.__context__.pop(0)
    self.__context__.append((f'{username}: {message}', completion[0]))

    self.__update_log__(message, completion)

  def add_side_prompt(self, side_prompt):
    self.__side_prompts__.pop(0)
    self.__side_prompts__.append(side_prompt)

if __name__ == "__main__":
  username = config.get('GENERAL', 'username')
  scenario = choice(txt_to_list('prompts\scenarios.txt'))
  aiko = AIko('Aiko', 'prompts\AIko.txt', scenario)
  while True:
    message = input(f'{username}: ')
    if breaker.lower() in message.lower():
      break
    aiko.interact(message, username)