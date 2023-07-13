"""
Streamlabs.py

Requirements:
- AIko.py (130alpha or greater) and its requirements.
- VoiceLink.py (050 or greater) and its requirements.
- AikoINIhandler.py (20 or greater) and its requirements.

txt files:
- AIko.txt
- spontaneous_messages.txt

Changelog:

010:
- Reorganized definitions. Now, functionality needed for the interaction loop are defined under if __name__ = '__main__'
section.
- Spontaneous message prompts are deleted from the pool list when picked, to prevent AIko from receiving the same
spontaneous message prompt multiple times.
011:
- MasterQueue object is now passed as a parameter to the interaction loop functions, instead of being passed as a global.
- Spontaneous messages min and max time interval are now configurable.
012:
- AIko now reads chat messages before answering them.
- Side prompts can be added through the press of the Page Up button.
- The script can also be terminated if the breaker phrase is written in the side prompt text box.
- Chat message cooldown times are now configurable.
- Mic message expiration time is also configurable.
013:
- Added Thread to handle remote side prompt receiver.
014:
- Moved local side prompting int oa separate thread.
- Local side prompting now has option for immediate completions.
- Speech recognition starts disabled by default.
015:
- Spontaneous prompts in the interaction loop now make use of the keyword system from AIko 130alpha.
016:
- Reverted spontaneous prompts back to how they were before 015. Keywords should be included in the txt file instead -
this allows better flexibility.
"""
import os
import time
import AIko
import random
import socket
import pytchat       
import keyboard
from pytimedinput import timedInput      
from configparser import ConfigParser
from AikoINIhandler import handle_ini     
from threading import Thread, Lock, Event                                          
from VoiceLink import say, start_speech_recognition, stop_speech_recognition
# ----------------------------------------------------------------------------
def is_empty_string(string : str):
    return string == ''                                                                                                                               
# ----------------------------------------------------------------------------
class MessageQueue: 
    """
    A class representing a thread-safe message queue.

    Public methods:
    - is_empty(): Checks if the message queue is empty.
    - add_message(message: str): Adds a message to the queue.
    - get_next(): Retrieves and removes the next message from the queue.
    """
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
    __instance__ = None
    __lock__ = Lock()

    def __new__(cls):
        """
        Ensures that only one instance of the class can be created.
        """
        if cls.__instance__ is None: 
            with cls.__lock__:
                if not cls.__instance__:
                    cls.__instance__ = super().__new__(cls)
                    cls.__instance__.__initialized__ = False
        return cls.__instance__

    def __init__(self):
        if (self.__initialized__):
            return
        self.__initialized__ = True

        self.__msg__ = ''
        self.__lock__ = Lock()
        self.__switch_evt__ = Event()

        # gets message expiration time from config
        config = ConfigParser()
        config.read('AikoPrefs.ini')

        self.__expiration_time__ = config.getfloat('LIVESTREAM', 'voice_message_expiration_time')

        # starts separate thread to manage expiration
        Thread(target = self.__expiration_countdown__).start()

    def __expiration_countdown__(self):
        timer_start = time.time()
        while True:
            timer_now = time.time()

            if self.__switch_evt__.is_set():
                timer_start = time.time()
                self.__switch_evt__.clear()

            if (timer_now - timer_start) >= self.__expiration_time__:
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
    A thread-safe class representing a message pool with limited capacity.

    Public Methods:
        add_chat_message(item: str) -> None:
            Adds a chat message to the message pool. If the pool is already at maximum capacity,
            the oldest message is removed to make room for the new message.

        pick_chat_message() -> str:
            Picks a random chat message from the message pool and returns it. The picked message
            is removed from the pool. If the pool is empty, an empty string is returned.
    """ 
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
    __instance__ = None
    __lock__ = Lock()

    def __new__(cls):
        """
        Ensures that only one instance of the class can be created.
        """
        if cls.__instance__ is None: 
            with cls.__lock__:
                if not cls.__instance__:
                    cls.__instance__ = super().__new__(cls)
                    cls.__instance__.__initialized__ = False
        return cls.__instance__

    def __init__(self):
        if (self.__initialized__):
            return

        self.__initialized__ = True

        self.__system_messages__ = MessageQueue()
        self.__mic_messages__ = MessageContainer()
        self.__chat_messages__ = MessagePool()

        self.__allow_chat__ = True

        # gets chat cooldown times from config
        config = ConfigParser()
        config.read('AikoPrefs.ini')

        self.__chat_min_cooldown__ = config.getint('LIVESTREAM', 'chat_min_cooldown')
        self.__chat_max_cooldown__ = config.getint('LIVESTREAM', 'chat_max_cooldown')

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
            cooldown_time = random.randint(self.__chat_min_cooldown__, self.__chat_max_cooldown__)
            Thread(target=self.__chat_cooldown__, kwargs={'cooldown': cooldown_time}).start()
            return ("chat", self.__chat_messages__.pick_message())

        return ('', '')
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    aiko = AIko.AIko('Aiko', 'prompts\AIko.txt')
    # ---------------------- CONTINOUSLY THREADED FUNCTIONS ------------------
    def thread_parse_chat(queue : MasterQueue, config : ConfigParser, chat : pytchat.core.PytchatCore):
        while chat.is_alive():

            for c in chat.get().sync_items():

                queue.add_message(f'{c.author.name}: {c.message}', "chat")
                print(f'\nAdded chat message to queue:\n{c.message}\n')

            # to keep CPU usage from maxing out
            time.sleep(0.1)
            
    def thread_speech_recognition(queue : MasterQueue, config : ConfigParser):
        username = config.get('GENERAL', 'username')
        hotkey = config.get('LIVESTREAM', 'toggle_listening')

        def parse_event(evt):
            event = str(evt)

            keyword = 'text="'
            stt_start = event.index(keyword)
            stt_end = event.index('",')
            
            message = event[stt_start + len(keyword):stt_end]

            if message != '':
                queue.add_message(f'{username}: {message}', "mic")
                print(f'\nAdded mic message to queue:\n{message}\n')

        keyboard.wait(hotkey)
        print('\nEnabled speech recognition.\n')
        time.sleep(0.1)

        start_speech_recognition(
            parse_func=parse_event,
            hotkey=hotkey
            )

    def thread_spontaneus_messages(queue : MasterQueue, config : ConfigParser):
        system_prompts = AIko.txt_to_list('prompts\spontaneous_messages.txt')

        min_time = config.getint('SPONTANEOUS_TALKING', 'min_time')
        max_time = config.getint('SPONTANEOUS_TALKING', 'max_time')

        while True:
            try:
                message = system_prompts.pop(random.randint(0, len(system_prompts) - 1))
            except:
                break
            time.sleep(random.randint(min_time, max_time))
            queue.add_message(message, "system")

    def thread_remote_side_prompt_receiver(queue : MasterQueue):
        # ------------ Set Up ----------------
        port = 5004
        server_ip = '26.124.79.180'    # Ulaidh's ID (FOR RCHART TO USE)
        #server_ip = '26.246.74.120'     # Rchart's ID (FOR ULAIDH TO USE)
        # ------------------------------------

        while True:

            try:
                # ------- TCP IP protocol -------
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((server_ip, port))
                msg = s.recv(1024)
                # -------------------------------

                message = msg.decode()[:-1]
                completion_option_selected = msg.decode()[-1]

                if completion_option_selected == '1':
                    queue.add_message(message, "system")

                elif completion_option_selected == '2':
                    aiko.add_side_prompt(message)

                else:
                    print('Remote side prompt received but something went wrong. Side prompt ABORTED!')

                # disconnect the client
                s.close()
            except:
                pass
            time.sleep(0.1)

    def thread_local_side_prompting(queue : MasterQueue, config : ConfigParser):
        global aiko

        breaker = config.get('GENERAL', 'breaker_phrase').lower()
        hotkey = config.get('LIVESTREAM', 'side_prompt')

        while True:
            keyboard.wait(hotkey)
            message, unused = timedInput(f"\nWrite a side prompt, or {breaker.upper()} to exit the script:\n - ", 9999)
            if breaker in message.lower():
                os._exit(0)
            option, unused = timedInput(f"\nPlease select an option to send the side prompt under:\n1 - Generate completion immediately\n2 - Inject information into Aiko's memory\n3 - Abort message.\n\nOption: ", 9999)
            if option == '1':
                queue.add_message(message, "system")
            elif option == '2':
                aiko.add_side_prompt(message)  

    def thread_talk(queue : MasterQueue):
        global aiko

        while True:
            msg_type, message = queue.get_next()

            if is_empty_string(message):
                continue 

            if msg_type == 'chat':
                say(message)

            print()
            aiko.interact(message, use_system_role = msg_type == "system")
            print()

            time.sleep(0.1)    
    # --------------------------------------------------------------------------
    handle_ini()
    
    queue = MasterQueue()
    
    config = ConfigParser()
    config.read('AikoPrefs.ini')

    Thread(target = thread_remote_side_prompt_receiver, kwargs = {'queue': queue}).start()
    Thread(target = thread_local_side_prompting, kwargs = {'queue': queue, 'config': config}).start()

    Thread(target = thread_parse_chat, kwargs = {'queue': queue, 'config': config, 'chat': pytchat.create(video_id=config.get('LIVESTREAM', 'liveid'))}).start()
    Thread(target = thread_speech_recognition, kwargs = {'queue': queue, 'config': config}).start()
    Thread(target = thread_spontaneus_messages, kwargs = {'queue': queue, 'config': config}).start()
    Thread(target = thread_talk, kwargs = {'queue': queue}).start()

    print('All threads started.')