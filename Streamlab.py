"""
Streamlabs.py

Requirements:
- AIko.py (112alpha or greater) and its requirements.
- VoiceLink.py (050 or greater) and its requirements.

txt files:
- AIko.txt
- spontaneous_messages.txt

Changelog:

003:
- Included interaction loop for livestreaming.
- Added spontaneous talking feature.
- Removed unused imports.
- Included versification.
004:
- Fixed spontaneous talking feature not being actually started.
- Added printout to let user know when all threads have been started.
005:
- Added username parameter to thread_speech_recognition() function.
- Messages stored in the MessageContainer class now have an expiration time.
006:
- Fixed logic error where messages in MessageContainer would expire before they should.
"""
import time
import AIko
import random
import pytchat                 
from configparser import ConfigParser   
from threading import Thread, Lock, Event                                          
from VoiceLink import say, start_speech_recognition, stop_speech_recognition                                                                                                                             
# ----------------------------------------------------------------------------
class MessageQueue: 
    """
    A singleton class representing a thread-safe message queue. Only one instance of this class can exist.

    Public methods:
    - is_empty(): Checks if the message queue is empty.
    - add_message(message: str): Adds a message to the queue.
    - get_next(): Retrieves and removes the next message from the queue.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        """
        Ensures that only one instance of the class can be created.
        """
        if cls._instance is None: 
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.__queue__ = []
        self.__lock__ = Lock()

    def is_empty(self):
        """
        Checks if the message queue is empty.

        Returns:
        - True if the queue is empty, False otherwise.
        """
        return len(self.__queue__) == 0

    def add_message(self, message : str):
        """
        Adds a message to the queue.

        Args:
        - message: A string representing the message to be added.
        """
        with self.__lock__:
            self.__queue__.append(message)

    def get_next(self):
        """
        Retrieves and removes the next message from the queue.

        Returns:
        - The next message from the queue as a string.
        - An empty string if the queue is empty.
        """
        with self.__lock__:
            if not self.is_empty():
                return self.__queue__.pop(0)
            return ''
  
class MessageContainer:
    """
    A singleton class that provides thread-safe storage for a temporary message. 
    Only one instance of the class can exist.

    Public Methods:
    - switch_message(message: str): Sets the message to the given value.
    - get_message(): Retrieves and clears the stored message.
    - has_message(): Checks if there is a stored message.

    """
    _instance = None
    _lock = Lock()

    _thread_started = False

    def __new__(cls):
        """
        Ensures that only one instance of the class can be created.
        """
        if cls._instance is None: 
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.__msg__ = ''
        self.__lock__ = Lock()
        self.__switch_evt__ = Event()
        self.__expiration_time__ = 10.0
        
        # to make sure the thread can only be started once
        if not MessageContainer._thread_started:
            Thread(target = self.__expiration_countdown__).start()
            MessageContainer._thread_started = True

    def __expiration_countdown__(self):
        timer_start = time.time()
        while True:
            timer_now = time.time()

            if self.__switch_evt__.is_set():
                timer_start = time.time()
                self.__switch_evt__.clear()

            if (timer_now - timer_start) >= 10.0:
                with self.__lock__:
                    self.__msg__ = ''
                
            time.sleep(0.1)

    def switch_message(self, message : str):
        """
        Sets the message to the given value. The message will expire after a set amount of seconds.

        Args:
        - message: The message to be stored.
        """
        with self.__lock__:
            self.__msg__ = message
            self.__switch_evt__.set()

    def has_message(self):
        """
        Checks if there is a stored message.

        Returns:
        - True if a message is stored, False otherwise.
        """
        return self.__msg__ != '' 
    
    def get_message(self):
        """
        Retrieves and clears the stored message.

        Returns:
        - The stored message, or an empty string if no message is stored.
        """
        with self.__lock__:
            helper = self.__msg__
            self.__msg__ = ''
            return helper

class MessagePool:
    """
    A thread-safe singleton class representing a message pool with limited capacity. Only one instance of this class
    can exist.

    Public Methods:
        add_chat_message(item: str) -> None:
            Adds a chat message to the message pool. If the pool is already at maximum capacity,
            the oldest message is removed to make room for the new message.

        pick_chat_message() -> str:
            Picks a random chat message from the message pool and returns it. The picked message
            is removed from the pool. If the pool is empty, an empty string is returned.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        """
        Ensures that only one instance of the class can be created.
        """
        if cls._instance is None: 
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
        
    def __init__(self):
        self.__pool__ = AIko.create_limited_list(10)
        self.__lock__ = Lock()

    def is_empty(self):
        return self.__pool__[-1] == '' and self.__pool__[0] == ""

    def add_message(self, message : str):
        """
        Adds a chat message to the message pool. If the pool is already at maximum capacity,
        the oldest message is removed to make room for the new message.

        Args:
            item (str): The chat message to be added.
        """
        with self.__lock__:
            self.__pool__.pop(0)
            self.__pool__.append(message)

    def pick_message(self):
        """
        Picks a random chat message from the message pool and returns it. The picked message
        is removed from the pool. If the pool is empty, an empty string is returned.

        Returns:
            The picked chat message as a string. If the pool is empty, an empty string is returned.
        """
        helper = ''
        with self.__lock__:
            if not self.is_empty():
                while True:
                    index = random.randint(0, len(self.__pool__) - 1)
                    helper = self.__pool__[index]
                    self.__pool__[index] = ''

                    if helper != '':
                        break
            return helper
# ----------------------------------------------------------------------------
def is_empty_string(string : str):
    return string == ''  

class MasterQueue:
    """
    A singleton class which acts as a priority queue to control and return specific types of messages.
    The message types and the priority order are the following:

    - system (handled by the MessageQueue class)
    - mic (handled by the MessageContainer class)
    - chat (handled by the MessagePool class)

    'Chat' type messages have a special propriety - they have a cooldown time after being initially returned. The queue
    will act as if empty if there are no other types of message to return and 'chat' is on cooldown.

    Public Methods:
    - add_message(message: str, message_type: str): Adds a message to the master queue.
    - get_next(): Retrieves the next message from the master queue based on priority.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        """
        Ensures that only one instance of the class can be created.
        """
        if cls._instance is None: 
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.__system_messages__ = MessageQueue()
        self.__mic_messages__ = MessageContainer()
        self.__chat_messages__ = MessagePool()
        self.__allow_chat__ = True

    def __chat_cooldown__(self, cooldown : int):
        self.__allow_chat__ = False
        time.sleep(cooldown)
        self.__allow_chat__ = True

    def add_message(self, message : str, message_type : str):
        """
        Adds a message to the master queue based on its type.

        Args:
        - message: A string representing the message to be added.
        - message_type: A string indicating the type of the message ('system', 'mic', 'chat').

        Raises:
        - TypeError: If the message_type is not a valid type.
        """
        if message_type == "system":
            self.__system_messages__.add_message(message)
        elif message_type == "mic":
            self.__mic_messages__.switch_message(message)
        elif message_type == "chat":
            self.__chat_messages__.add_message(message)
        else:
            raise TypeError(f"{message_type} is not a valid message type")

    def get_next(self):
        """
        Retrieves the next message from the master queue based on priority.

        Returns:
        - A tuple containing the message type and the message content.
        - A tuple containing empty strings if there are no messages in the queue / 'chat' is in cooldown mode.
        """
        msg = self.__system_messages__.get_next()

        if not is_empty_string(msg):
            return ("system", msg)

        msg = self.__mic_messages__.get_message()

        if not is_empty_string(msg):
            return ("mic", msg)

        if self.__allow_chat__:
            Thread(target=self.__chat_cooldown__, kwargs={'cooldown': random.randint(2, 6)}).start()
            return ("chat", self.__chat_messages__.pick_message())

        return ('', '')
# ----------------------------------------------------------------------------
queue = MasterQueue()
# ---------------------- CONTINOUSLY THREADED FUNCTIONS ----------------------
def thread_parse_chat(chat):
    while chat.is_alive():

        for c in chat.get().sync_items():

            queue.add_message(f'{c.author}: {c.message}', "chat")
            #print(f'Added chat message to queue:\n{c.message}')

        # to keep CPU usage from maxing out
        time.sleep(0.1)
        
def thread_speech_recognition(hotkey : str, username : str):

    def parse_event(evt):
        event = str(evt)

        keyword = 'text="'
        stt_start = event.index(keyword)
        stt_end = event.index('",')
        
        message = event[stt_start + len(keyword):stt_end]

        if message != '':
            queue.add_message(f'{username}: {message}', "mic")
            #print(f'Added mic message to queue:\n{message}')

    start_speech_recognition(
        parse_func=parse_event,
        hotkey=hotkey
        )

def thread_spontaneus_messages():
    system_prompts = AIko.txt_to_list('prompts\spontaneous_messages.txt')

    while True:
        time.sleep(random.randint(30, 90))
        queue.add_message(random.choice(system_prompts), "system")

def thread_talk():
    aiko = AIko.AIko('Aiko', 'prompts\AIko.txt')
    while True:
        msg_type, message = queue.get_next()

        if is_empty_string(message):
            continue 

        aiko.interact(message, use_system_role = msg_type == "system")
        time.sleep(0.1)
# ----------------------------------------------------------------------------
if __name__ == '__main__':

    config = ConfigParser()
    config.read('AikoPrefs.ini')
    username = config.get('GENERAL', 'username')
    listen_hotkey = config.get('LIVESTREAM', 'toggle_listening')
    livestream_id = config.get('LIVESTREAM', 'liveid')

    chat = pytchat.create(video_id=livestream_id)

    Thread(target = thread_speech_recognition, kwargs = {'hotkey': listen_hotkey, 'username': username}).start()
    Thread(target = thread_parse_chat, kwargs = {'chat': chat}).start()
    Thread(target = thread_spontaneus_messages).start()
    Thread(target = thread_talk).start()

    print('All threads started.')