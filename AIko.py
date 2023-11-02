""" ==============================================================
AIko.py

Objects for interaction with custom-made AI characters.

Requirements:
- AIkoVoice.py (100 or greater) and its requirements
- AIkoINIhandler.py

pip install:
- openai
- func_timeout

txt files:
- AIko.txt
- key_openai.txt
- scenarios.txt

Changelog:

160beta:
- Added FrameOfMind class for handling frame of mind feature.
161beta:
- Added switch_personality method to Context class.
- Separated FrameOfMind class update_mood method into two separate methods: update_score and check_mood.
- Initial implementation of the frame of mind feature into the AIko class.
- Score class can now be given a starting value as an argument.
- Fixed typo in FOM class which caused errors when getting negative scores.
===================================================================
"""
# ----------------- Imports -----------------
import openai  # gpt3
from threading import Thread, Lock  # thread safe Score class
from datetime import datetime  # for logging
from configparser import ConfigParser  # ini file config
from AikoSentiment import sentiment_analysis  # for the mood system
from func_timeout import func_timeout, FunctionTimedOut  # for handling openAI ratelimit errors
import os  # gathering files from folder

# -------------------------------------------
# PLEASE set it if making a new build. for logging purposes
build_version = 'Aiko161beta'.upper()

# ------------- Set variables ---------------
# reads config file
config = ConfigParser()
config.read('AIkoPrefs.ini')
# Sets variable according to config
completion_timeout = config.getint('GENERAL', 'completion_timeout')

openai.api_key = open('keys/key_openai.txt', 'r').read().strip()


# -------------------------------------------


# -------------- Functions ------------------
def create_limited_list(length: int):
  """
  Returns a limited list of empty strings.
  """
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


def generate_gpt_completion(messages: list):
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
            model="gpt-3.5-turbo",
            messages=messages
        )

        completion = request.choices[0].message.content
        token_usage = (request.usage.prompt_tokens, request.usage.completion_tokens, request.usage.total_tokens)

        return (completion, token_usage)

    except openai.error.RateLimitError as e:
        print('Aiko.py:')
        print(e)
        print()

        return ('', (0, 0, 0))


def generate_gpt_completion_timeout(messages: list, timeout: int = completion_timeout):
    """
    Requests a completion under a set timeout in seconds.
    If the first request fails to return a value under the set time out value, a second request is made.
    Useful for circumventing RateLimit errors when the OpenAI API is overloaded.

    Returns a tuple containing:
    - Str, Completion text
    - Tuple, usage data in tokens.

    """

    try:
        completion_request = func_timeout(timeout, generate_gpt_completion, kwargs={'messages': messages})
    except FunctionTimedOut:
        completion_request = generate_gpt_completion(messages)

    return (completion_request)


def txt_to_list(txt_filename: str):
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


def gather_txts(directory: str):
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


# ----------------- Classes -------------------
class MessageList:
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

    def __init__(self, slots: int):
        self.__message_list__ = create_limited_list(slots)

    def __str__(self):
        items = self.get_items()
        items_as_strings = []

        for item in items:
            items_as_strings.append(str(item))

        return '\n'.join(items_as_strings)

    def add_item(self, item: str, role: str):
        """
          Removes the oldest item in the list and appends a new one.

          Attributes:
              item (str): The message to be added.
              role (str): The role the message will be under when requesting a completion. Can be either "system",
              "user" or "assistant".
        """
        self.__message_list__.pop(0)
        self.__message_list__.append({"role": role, "content": item})

    def delete_item(self, index: int):
        self.__message_list__[index] = ''

    def get_items(self) -> list:
        """
          Returns the populated items of the list.
        """
        populated_items = []

        for item in self.__message_list__:
            if item != '':
                populated_items.append(item)
        return populated_items

    def append_items(self, existing_list: list):
        """
          Appends the populated items of the lists to an existing list.
          USE WITH CAUTION: This method will MODIFY the list you give it as a parameter. It has no return value
        """
        for item in self.__message_list__:
            if item != '':
                existing_list.append(item)

    def is_empty(self) -> bool:
        return self.__message_list__[-1] == ''

    def get_reference(self):
        """
        Returns a reference to this class' private list object. Useful for display/consulting needs - if you want to
        modify the list, use the class' built in methods.
        """
        return self.__message_list__


class BlackBox:

    def __init__(self):
        self.personal_key_word = ['you']
        self.preference_key_word = ['favorite', 'like', 'where', 'old']

    def message_meets_criteria(self, message: str):
        l_msg = message.lower()
        # if 'what is' in message.lower():
        if any(x in l_msg for x in self.personal_key_word) and any(y in l_msg for y in self.preference_key_word):
            return True

        return False


class Context:

    def __init__(self, scenario: str, sp_slots: int = 5, mem_slots: int = 10):
        self.__personalities = gather_txts('prompts/personalities')
        self.__personality = self.__personalities['AIKO']

        self.context = MessageList(mem_slots)
        self.side_prompts = MessageList(sp_slots)
        self.scenario = MessageList(1)

        self.scenario.add_item(scenario, "system")
        self.__profile = txt_to_string('prompts/profile.txt')

    def __append_message_lists(self, list_to_append: list):
        self.scenario.append_items(list_to_append)
        self.side_prompts.append_items(list_to_append)
        self.context.append_items(list_to_append)

    def build_context(self, use_profile: bool = False):
        """
          Builds context dictionary list with the currently relevant information.
        """
        messages = [{"role": "system", "content": self.__personality}]
        self.__append_message_lists(messages)

        if use_profile:
            messages.append({"role": "system", "content": self.__profile})

        return messages

    def switch_personality(self, personality: str):
        personality = personality.upper()
        if personality not in self.__personalities:
            raise ValueError('Invalid personality.')

        self.__personality = self.__personalities[personality]


class Score:

    def __init__(self, start: int = 0):
        self.__score = start
        self.__lock = Lock()

    def update_score(self, value: int):
        with self.__lock:
            self.__score += value

    @property
    def score(self):
        return self.__score


class Log:
    def __init__(self, personality_file: str):
        self.__log = self.__create_log(personality_file)

    def __create_log(self, personality_file: str):
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
        time = time.replace(' ', '_').replace('/', '-').replace(':', '-')

        log_filename = r'log/{}.txt'.format(time)

        with open(r'log/{}.txt'.format(time), 'w') as log:
            log.write(f'{hour}\n')
            log.write('\n')
            log.write(f'AIKO.PY BUILD VERSION: {build_version} \n')
            log.write(f'{personality_file}: \n')
            with open(personality_file, 'r') as aiko_txt:
                for line in aiko_txt:
                    log.write(line)
            log.write('\n')
            log.write('\n')
            log.write(f'---------------END OF "{personality_file}"---------------\n')
            log.write('\n')

        return log_filename

    def update_log(self, user_string: str, completion_data: tuple):
        """
          Updates the log file with the user's input and the generated output.

          Args:
              user_string (str): The user's input message.
              completion_data (tuple): A tuple containing the generated output and token usage information.
        """
        time = datetime.now()
        hour = f'[{time.hour}:{time.minute}:{time.second}]'

        self.__session_token_usage__ += completion_data[1][2]

        with open(self.__log, 'a') as log:
            log.write(f'{hour}\n')
            log.write('\n')
            log.write(f'Prompt: {user_string} --TOKENS USED: {completion_data[1][0]}\n')
            log.write(f'Output: {completion_data[0]} --TOKENS USED: {completion_data[1][1]}\n')
            log.write(f'Total tokens used: {completion_data[1][2]}\n')
            log.write('\n')
            log.write(f'Tokens used this session: {self.__session_token_usage__}\n')
            log.write('\n')


class FrameOfMind:
    """
    A class for managing and analyzing the mood of a conversation based on sentiment analysis scores.

    The `FrameOfMind` class allows you to track and update the mood of a conversation by assigning sentiment scores to
    text messages and determining the current mood state based on defined score thresholds.

    Arguments:
        - thresholds (dict, optional): A dictionary specifying mood score ranges (range objects) for different moods.
        Example {'angry': range(-10000, -2500), 'neutral': range(-2500, 2500), 'happy': range(2500, 10000)}.
    Methods:
        - update_score(self, message: str): Update the mood score based on the sentiment of a given message.
        - check_mood(self): Check and print the current mood state and mood score.
    """
    def __init__(self, thresholds: dict = None):
        self.__mood_score = Score()

        # sets default thresholds if no threshold dictionary is given
        if thresholds is None:
            self.__thresholds = {
                'negative': range(-100000, -2500), 'neutral': range(-2500, 2500), 'positive': range(2500, 100000)
                }
        else:
            self.__thresholds = thresholds

        # sets starting mood
        self.__state = self.check_mood()

    def update_score(self, message: str):
        # calculate score of given message
        sentiment, points = sentiment_analysis(message)
        # update score value

        if sentiment == 'positive':
            #case 'positive':
            self.__mood_score.update_score(points)
        elif sentiment == 'negative':
            self.__mood_score.update_score(points - points * 2)

    def check_mood(self):
        print('CURRENT SCORE:', self.__mood_score.score)
        # return current mood by checking which threshold the score is currently in
        for state, threshold in self.__thresholds.items():
            if self.__mood_score.score in threshold:
                self.__state = state
                return state


class AIko:
    """
      A class that can be used for interacting with custom-made AI characters.

      Attributes:
          character_name (str): The name of the AI character.

      Parameters:
          scenario (str): The scenario in which the character currently finds itself in.
          personality_filename (str): The filename of the personality file.
          sp_slots (int): The max number of side prompt slots.
          mem_slots (int): The max number of context slots.

      Methods:
          interact(username: str, message: str):
              Interacts with the AI character by providing a username and a message.
          add_side_prompt(side_prompt : str):
              Injects a side prompt into the character's memory.
          change_scenario(scenario : str):
              Changes the current scenario.
    """

    def __init__(self, character_name: str, scenario: str = '', sp_slots: int = 5,
                 mem_slots: int = 10):
        self.character_name = character_name
        self.__black_box = BlackBox()
        self.context = Context(scenario, sp_slots, mem_slots)

        # frame of mind
        thresholds = {
            'aiko_hulk': range(-100000, -1500),
            # 'aiko_angry_lvl2': range(-4000, -3500),
            'aiko_angry_lvl1': range(-1500, -1000),
            'aiko': range(-1000, 1000),
            'aiko_happy_lvl1': range(1000, 100000),
        }

        self.__mood = FrameOfMind(thresholds)
        self.__log = Log('prompts/personalities/aiko.txt')
        self.__keywords = gather_txts('prompts/keywords')

    def change_scenario(self, scenario: str):
        self.context.scenario.add_item(scenario, 'system')

    def add_side_prompt(self, side_prompt: str):
        self.context.side_prompts.add_item(side_prompt, 'system')

    def has_keyword(self, message: str):
        for keyword in self.__keywords:
            if message.startswith(keyword):
                return (True, {"role": "system", "content": self.__keywords[keyword]}, keyword)

        return (False, None, None)

    def interact(self, message: str, use_system_role: bool = False):
        """
          Interacts with the AI character by providing a message.
        """
        # performs sentiment analysis on message to update her mood, done on a separate thread to avoid extra latency
        Thread(target=self.__mood.update_score, kwargs={'message': message}).start()

        use_profile = self.__black_box.message_meets_criteria(message)
        messages = self.context.build_context(use_profile)

        has_keyword = False
        # appends the message under the chosen role (user/system)
        if use_system_role:
            # checks for keyword
            has_keyword, keyword_instructions, keyword = self.has_keyword(message)
            if has_keyword:
                messages.append(keyword_instructions)

            # appends as system
            messages.append({"role": "system", "content": message})
        else:
            # appends as user
            messages.append({"role": "user", "content": message})

        # requests completion
        completion = generate_gpt_completion_timeout(messages)
        output = completion[0]

        # saves interaction to context
        if use_system_role:
            self.context.context.add_item(output, "assistant")
        else:
            self.context.context.add_item(message, "user")
            self.context.context.add_item(output, "assistant")

        self.__log.update_log(message, completion)

        # parses keyword out of output, if using keywords
        if has_keyword and f'{keyword.lower()}:' in output.lower()[:len(keyword) + 2]:
            output = output[len(keyword) + 1:]
        # parses character name (EG "Aiko: bla bla") out of output
        if f'{self.character_name}:' in output[:len(self.character_name) + 2]:
            output = output[len(self.character_name) + 1:]

        # updates personality after checking current mood
        personality = self.__mood.check_mood()
        self.context.switch_personality(personality)
        print('CURRENT MOOD:', personality)

        return output
# -------------------------------------------


if __name__ == '__main__':
    mood = FrameOfMind()
    print('Ulaidh said: I love you.')
    for i in range(0, 2):
        mood.update_score('I love you.')
        print('current mood:', mood.check_mood())
