""" ==============================================================
AIko.py

Requirements:
- VoiceLink.py and its requirements
- AikoINIhandler.py

pip install:
- openai
- func_timeout

txt files:
- AIko.txt
- key_openai.txt
- scenarios.txt

Changelog:

110alpha:
- Added messageList class for handling information such as context lists and side prompts.
- The scenario is no longer a public attribute of the AIko class. To change it, one must use the change_scenario()
method.
111alpha:
- Time is now only reported at the beginning of each log report entry, instead of at every line.
- Removed 'Starting...' printout when importing the script.
- Fixed generate_gpt_completion_timeout() function and switched to using it in the AIko class.
112alpha:
- Removed 'username' parameter from interact() AIko method. Usernames should now be handled externally.
113alpha:
- dynamic_scenario setting setting now actually affects the interaction loop.
- session_token_usage is now a private attribute of the AIko class instead of a global.
- Removed unused setting imports.
114alpha:
- Reimplemented silence breaker into the local interaction loop.
120alpha:
- Implemented profile system, that adds Aiko particular tastes into the prompt
===================================================================
""" 

# PLEASE set it if making a new build. for logging purposes
build_version = ('Aiko113alpha').upper() 


# -------------------------------------------
if __name__ == '__main__':
  from AikoINIhandler import handle_ini
  handle_ini()


# ----------------- Imports -----------------
import openai                          # gpt3
from VoiceLink import say              # text to speech function
from datetime import datetime          # for logging
from pytimedinput import timedInput    # input with timeout
from random import choice, randint     # random
from configparser import ConfigParser  # ini file config
from func_timeout import func_timeout, FunctionTimedOut # for handling openAI ratelimit errors
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
        def change_scenario(scenario : str):
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

    #self.__profile__ = messageList(1)
    self.__profile__ = txt_to_string('prompts\profile.txt')

    self.__session_token_usage__ = 0

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

  def interact(self, message : str, use_system_role : bool = False, use_profile : bool = False):
    """
      Interacts with the AI character by providing a message.
    """
    messages = [{"role":"system", "content": self.__personality__}]

    if use_profile:
      messages += [{"role":"system", "content": self.__profile__}]
    messages += self.__scenario__.get_items()
    messages += self.__side_prompts__.get_items()
    messages += self.__context__.get_items()

    if use_system_role:
      messages.append({"role":"system", "content": message})
    else:
      messages.append({"role":"user", "content": message})

    completion = generate_gpt_completion_timeout(messages)
    print(completion[0])

    # parses completion (when appliable) to be fed to text to speech
    if f'{self.character_name}:' in completion[0][:len(self.character_name) + 2]:
      say(completion[0][len(self.character_name) + 1:])

    else:
      say(completion[0])

    if use_system_role:
      self.__context__.add_item(completion[0], "assistant")
    else:
      self.__context__.add_item(message, "user")
      self.__context__.add_item(completion[0], "assistant")

    self.__update_log__(message, completion)

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
  aiko = AIko('Aiko', 'prompts\AIko.txt')
  aiko.add_side_prompt('Aiko prefers cats over dogs. Especially siamese cats.')

  dynamic_scenarios = config.getboolean('GENERAL', 'dynamic_scenarios')
  if dynamic_scenarios:
    scenarios = txt_to_list('prompts\scenarios.txt')
    aiko.change_scenario(choice(scenarios))

  username = config.get('GENERAL', 'username')
  breaker = config.get('GENERAL', 'breaker_phrase')

  spontaneous_messages = txt_to_list('prompts\spontaneous_messages.txt')

  while True:
    message, timeout = timedInput(f'{username}: ', randint(60, 300))
    use_profile = False
    if 'what is' in message.lower():
      use_profile = True

    if timeout:
      aiko.interact(choice(spontaneous_messages), True)
    elif breaker.lower() in message.lower():
      break
    else:
      prompt = f'{username}: {message}'
      aiko.interact(prompt, False, use_profile)