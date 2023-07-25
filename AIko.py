""" ==============================================================
AIko.py

Objects for interaction with custom made AI characters.

Requirements:
- VoiceLink.py (100 or greater) and its requirements
- AikoINIhandler.py

pip install:
- openai
- func_timeout

txt files:
- AIko.txt
- key_openai.txt
- scenarios.txt

Changelog:

140beta:
- AIko.interact() method no longer prints or voices the completion. Instead, it returns it.
- As a consequence of the above change, the read_aloud parameter has been removed.
- Context is now built in a separate method - AIko.__build_context(), which returns the context dictionary list.
141beta:
- Placed profile on further indexes of the context list, to make sure the information stays relevant to the AI.
142beta:
- Fixed exception raised when trying to use system messages.
142beta:
- Updated black box simulator. Now it considers personal and preference keywords.
143beta:
- Updated to work with latest VoiceLink.
===================================================================
""" 
# PLEASE set it if making a new build. for logging purposes
build_version = ('Aiko143beta').upper() 
# -------------------------------------------
if __name__ == '__main__':
  from AikoINIhandler import handle_ini
  handle_ini()
# ----------------- Imports -----------------
import openai                          # gpt3
from VoiceLink import Synthesizer      # text to speech function
from datetime import datetime          # for logging
from pytimedinput import timedInput    # input with timeout
from random import choice, randint     # random
from configparser import ConfigParser  # ini file config
from func_timeout import func_timeout, FunctionTimedOut # for handling openAI ratelimit errors
import os                              # gathering files from folder
# -------------------------------------------



# ------------- Set variables ---------------
# reads config file
config = ConfigParser()
config.read('AikoPrefs.ini')
# Sets variable according to config
completion_timeout = config.getint('GENERAL', 'completion_timeout')
# Set OpenAPI key here
openai.api_key = open("keys/key_openai.txt", "r").read().strip('\n')
# -------------------------------------------



# -------------- Functions ------------------
def create_limited_list(length : int):
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
    completion_request = func_timeout(timeout, generate_gpt_completion, kwargs = {'messages': messages})
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

def gather_txts(directory : str):
  """
  Gather text files from a directory and store their contents in a dictionary.

  Args:
      directory (str): The path to the directory containing the text files.

  Returns:
      dict: A dictionary where the keys are the modified filenames (uppercase, without file extension or spaces),
            and the values are the contents of the corresponding text files.

  Example:
      Given a directory 'my_folder' containing the following files:
      - file1.txt
      - file2.txt

      The function gather_txts('my_folder') would return a dictionary like this:
      {
          'FILE1': 'Contents of file1',
          'FILE2': 'Contents of file2'
      }
  """
  txts = {}

  # adds each txt file in folder to dictionary
  for filename in os.scandir(directory):

    # formats the filename to be added as the dictionary's key
    txt_name = str(filename)
    txt_name = txt_name[1:-1]
    txt_name = txt_name.replace('DirEntry', '')
    txt_name = txt_name.replace('.txt', '')
    txt_name = txt_name.replace("'", '')
    txt_name = txt_name.replace(' ', '')
    txt_name = txt_name.upper()

    # adds the contents of the txt to the dictionary using the filename as key
    contents = txt_to_string(filename)
    txts[txt_name] = contents

  return txts
# -------------------------------------------



# ----------------- Class -------------------
class messageList:
  """
  A class that holds a limited list of messages meant for prompting GPT.

  Parameters:
      slots (int): The maximum number of slots the list can hold.

  Methods:
      add_item(item : str, role : str):
          Removes the oldest item in the list and appends a new one.
      get_items() -> list:
          Returns the populated items of the list.
      is_empty() -> bool:
          Whether items have been added to the list or not.
  """
  def __init__(self, slots : int):
    self.__message_list__ = create_limited_list(slots)

  def __str__(self):
    items = self.get_items()
    items_as_strings = []

    for item in items:
      items_as_strings.append(str(item))

    return '\n'.join(items_as_strings)

  def add_item(self, item : str, role : str):
    """
      Removes the oldest item in the list and appends a new one.

      Attributes:
          item (str): The message to be added.
          role (str): The role the message will be under when requesting a completion. Can be either "system",
          "user" or "assistant".
    """
    self.__message_list__.pop(0)
    self.__message_list__.append({"role": role, "content": item})

  def get_items(self) -> list:
    """
      Returns the populated items of the list.
    """
    populated_items = []

    for item in self.__message_list__:
      if item != '':
        populated_items.append(item)
    return populated_items

  def is_empty(self) -> bool:
    return self.__message_list__[-1] == ''

class AIko:
  """
    A class that can be used for interacting with custom made AI characters.

    Attributes:
        character_name (str): The name of the AI character.
        personality_file (str): The filename of the personality file.

    Parameters:
        scenario (str): The scenario in which the character currently finds itself in.  

    Methods:
        interact(username: str, message: str):
            Interacts with the AI character by providing a username and a message.
        add_side_prompt(side_prompt : str):
            Injects a side prompt into the character's memory.
        change_scenario(scenario : str):
            Changes the current scenario.
  """
  def __init__(self, character_name : str, personality_filename : str, scenario : str = ''):
    self.character_name = character_name
    self.personality_file = personality_filename

    self.__personality__ = txt_to_string(personality_filename)
    self.__log__ = self.__create_log__()

    self.__context__ = messageList(10)
    self.__side_prompts__ = messageList(5)

    self.__scenario__ = messageList(1)
    self.__scenario__.add_item(scenario, "system")

    self.__profile__ = txt_to_string('prompts\profile.txt')

    self.__keywords__ = gather_txts('prompts\keywords')

  def __create_log__(self):
    """
      Creates a log file and reports initial information.

      Returns:
          log_filename (str): The filename of the created log file.
    """
    global build_version

    self.__session_token_usage__ = 0

    time = datetime.now()
    hour = f'[{time.hour}:{time.minute}:{time.second}]'
    time = time.strftime("%d/%m/%Y %H:%M:%S")
    time = time.replace(' ','_').replace('/','-').replace(':','-')

    log_filename = r'log/{}.txt'.format(time)

    with open(r'log/{}.txt'.format(time), 'w') as log:
      log.write(f'{hour}\n')
      log.write('\n')
      log.write(f'AIKO.PY BUILD VERSION: {build_version} \n')
      log.write(f'{self.personality_file}: \n')
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
    time = datetime.now()
    hour = f'[{time.hour}:{time.minute}:{time.second}]'

    self.__session_token_usage__ += completion_data[1][2]

    with open(self.__log__, 'a') as log:
      log.write(f'{hour}\n')
      log.write('\n')
      log.write(f'Prompt: {user_string} --TOKENS USED: {completion_data[1][0]}\n')
      log.write(f'Output: {completion_data[0]} --TOKENS USED: {completion_data[1][1]}\n')
      log.write(f'Total tokens used: {completion_data[1][2]}\n')
      log.write('\n')
      log.write(f'Tokens used this session: {self.__session_token_usage__}\n')
      log.write('\n')

  def __build_context(self, message : str, use_system_role : bool = False):
    """
      Builds context dictionary list with the currently relevant information.
    """
    # Personality
    messages = [{"role":"system", "content": self.__personality__}]

    messages += self.__scenario__.get_items()
    messages += self.__side_prompts__.get_items()
    messages += self.__context__.get_items()

    # Black box simulator
    personal_key_word = ['you']
    preference_key_word = ['favorite', 'like']
    l_msg = message.lower()
    #if 'what is' in message.lower():
    if any(x in l_msg for  x in personal_key_word) and any(y in l_msg for y in preference_key_word):
      messages += [{"role":"system", "content": self.__profile__}]

    if use_system_role:

      # injects keyword instructions into context if keyword is present in the system prompt
      for keyword in self.__keywords__:
        if message.startswith(keyword):
          messages += [{"role":"system", "content": self.__keywords__[keyword]}]
          print('(Generating completion with keyword instructions...)')
          break

      # prompts message under system role
      messages.append({"role":"system", "content": message})

    else:
      messages.append({"role":"user", "content": message})

    return messages
  
  def interact(self, message : str, use_system_role : bool = False):
    """
      Interacts with the AI character by providing a message.
    """
    messages = self.__build_context(message, use_system_role)
    completion = generate_gpt_completion_timeout(messages)

    if use_system_role:
      self.__context__.add_item(completion[0], "assistant")
    else:
      self.__context__.add_item(message, "user")
      self.__context__.add_item(completion[0], "assistant")

    self.__update_log__(message, completion)

    # parses completion before returning it if character's name (E.G, "Aiko: bla bla") happens to be included
    if f'{self.character_name}:' in completion[0][:len(self.character_name) + 2]:
      return(completion[0][len(self.character_name) + 1:])

    return(completion[0])

  def add_side_prompt(self, side_prompt : str):
    """
      Injects a side prompt into the character's memory.
    """
    self.__side_prompts__.add_item(side_prompt, "system")

  def change_scenario(self, scenario : str):
    """
      Changes the current scenario.
    """
    self.__scenario__.add_item(scenario, "system")
# -------------------------------------------



# ------------------ Main -------------------
if __name__ == "__main__":
  # creates a Synthesizer object for voicing Aiko
  synthesizer = Synthesizer()

  # creates an AIko object
  aiko = AIko('Aiko', 'prompts\AIko.txt')
  aiko.add_side_prompt('Aiko prefers cats over dogs. Especially siamese cats.')

  # enables dynamic scenario if enabled in config
  dynamic_scenarios = config.getboolean('GENERAL', 'dynamic_scenarios')
  if dynamic_scenarios:
    scenarios = txt_to_list('prompts\scenarios.txt')
    aiko.change_scenario(choice(scenarios))

  username = config.get('GENERAL', 'username')
  breaker = config.get('GENERAL', 'breaker_phrase')

  spontaneous_messages = txt_to_list('prompts\spontaneous_messages.txt')

  # interaction loop
  while True:
    message, timeout = timedInput(f'{username}: ', randint(60, 300))
    use_system = False

    if timeout:
      prompt = choice(spontaneous_messages)
      use_system = True
    elif breaker.lower() in message.lower():
      break
    else:
      prompt = f'{username}: {message}'

    output = aiko.interact(prompt, use_system)
    print(f'Aiko:{output}')
    synthesizer.say(output)