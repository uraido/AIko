"""
AIkoStreamingTools.py

Requirements:
- AIko.py (140beta or greater) and its requirements.
- AIkoVoice.py (100 or greater) and its requirements.
- AIkoINIhandler.py (23 or greater) and its requirements.

Changelog:

031:
- Removed redundant double underlines from MasterQueue attribute names.
"""

# ----------------------------- Imports -------------------------------------
import time
import AIko
import random
from configparser import ConfigParser
from threading import Thread, Lock, Event
import socket
import re
# ----------------------------------------------------------------------------


def is_empty_string(string: str):
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
        self.__queue = []
        self.__lock = Lock()

    def is_empty(self):
        """
        Checks if the message queue is empty.

        Returns:
        - True if the queue is empty, False otherwise.
        """
        return len(self.__queue) == 0

    def add_message(self, message: str):
        """
        Adds a message to the queue.

        Args:
        - message: A string representing the message to be added.
        """
        with self.__lock:
            self.__queue.append(message)

    def get_next(self):
        """
        Retrieves and removes the next message from the queue.

        Returns:
        - The next message from the queue as a string.
        - An empty string if the queue is empty.
        """
        with self.__lock:
            if not self.is_empty():
                return self.__queue.pop(0)
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
        if self.__initialized__:
            return
        self.__initialized__ = True

        self.__msg__ = ''
        self.__lock__ = Lock()
        self.__switch_evt__ = Event()

        # gets message expiration time from config
        config = ConfigParser()
        config.read('AIkoPrefs.ini')

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

    def switch_message(self, message: str):
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
        add_message(item: str) -> None:
            Adds a message to the message pool. If the pool is already at maximum capacity,
            the oldest message is removed to make room for the new message.

        pick_message() -> str:
            Picks a random message from the message pool and returns it. The picked message
            is removed from the pool. If the pool is empty, an empty string is returned.
    """ 
    def __init__(self):
        self.__pool = AIko.create_limited_list(10)
        self.__lock = Lock()
        self.__paused = False

    def is_empty(self):
        for item in self.__pool:
            if item != '':
                return False
        return True

    def add_message(self, message: str):
        """
        Adds a message to the message pool. If the pool is already at maximum capacity,
        the oldest message is removed to make room for the new message.

        Args:
            message (str): The message to be added.
        """
        with self.__lock:
            self.__pool.pop(0)
            self.__pool.append(message)

    def pick_message(self):
        """
        Picks a random message from the message pool and returns it. The picked message
        is removed from the pool. If the pool is empty, an empty string is returned.

        Returns:
            The picked message as a string. If the pool is empty, an empty string is returned.
        """
        helper = ''
        with self.__lock:
            if not self.is_empty():
                while True:
                    index = random.randint(0, len(self.__pool) - 1)
                    helper = self.__pool[index]
                    self.__pool[index] = ''

                    if helper != '':
                        break
            return helper

    def edit_message(self, original_content: str, new_content: str):
        with self.__lock:
            if original_content in self.__pool:
                msg_index = self.__pool.index(original_content)
                self.__pool[msg_index] = new_content
            else:
                raise ValueError('Message does not exist in pool.')

    def delete_message(self, index: int):
        if index > 10:
            raise ValueError("Index can't be higher than 10.")

        self.__pool[index] = ''

    def get_pool_reference(self):
        return self.__pool

    def pause(self):
        """
        Pauses/unpauses the pool. When paused, the pool will maintain it's current state, without adding or returning
        any messages. If the add_message method is called during the pause state, the message will be added after the
        pool is un-paused.
        """
        if self.__paused:
            self.__paused = False
            self.__lock.release()
        else:
            self.__paused = True
            self.__lock.acquire()
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
    - add_message(message : str, message_type : str): Adds a message to the master queue.
    - edit_chat_message(original_content : str, new_content : str): Edit "chat" type messages by content.
    - get_next(): Retrieves the next message from the master queue based on priority.
    """
    __instance = None
    __lock = Lock()

    def __new__(cls):
        """
        Ensures that only one instance of the class can be created.
        """
        if cls.__instance is None:
            with cls.__lock:
                if not cls.__instance:
                    cls.__instance = super().__new__(cls)
                    cls.__instance.__initialized = False
        return cls.__instance

    def __init__(self):
        if self.__initialized:
            return

        self.__initialized = True

        self.__system_messages = MessageQueue()
        self.__mic_messages = MessageContainer()
        self.__chat_messages = MessagePool()

        self.__allow_chat = True

        # gets chat cooldown times from config
        config = ConfigParser()
        config.read('AIkoPrefs.ini')

        self.__chat_min_cooldown = config.getint('LIVESTREAM', 'chat_min_cooldown')
        self.__chat_max_cooldown = config.getint('LIVESTREAM', 'chat_max_cooldown')

    def __chat_cooldown__(self, cooldown : int):
        self.__allow_chat = False
        time.sleep(cooldown)
        self.__allow_chat = True

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
            self.__system_messages.add_message(message)
        elif message_type == "mic":
            self.__mic_messages.switch_message(message)
        elif message_type == "chat":
            self.__chat_messages.add_message(message)
        else:
            raise TypeError(f"{message_type} is not a valid message type")

    def get_chat_messages(self):
        """
        Useful for display/check needs. If you want to modify the object, use the MasterQueue's own methods.
        """
        return self.__chat_messages

    def edit_chat_message(self, original_content : str, new_content : str):
        self.__chat_messages.edit_message(original_content, new_content)

    def delete_chat_message(self, index: int):
        self.__chat_messages.delete_message(index)

    def get_next(self):
        """
        Retrieves the next message from the master queue based on priority.

        Returns:
        - A tuple containing the message type and the message content.
        - A tuple containing empty strings if there are no messages in the queue / 'chat' is in cooldown mode.
        """
        msg = self.__system_messages.get_next()

        if not is_empty_string(msg):
            return "system", msg

        msg = self.__mic_messages.get_message()

        if not is_empty_string(msg):
            return "mic", msg

        if self.__allow_chat:
            cooldown_time = random.randint(self.__chat_min_cooldown, self.__chat_max_cooldown)
            Thread(target=self.__chat_cooldown__, kwargs={'cooldown': cooldown_time}).start()
            return "chat", self.__chat_messages.pick_message()

        return '', ''


class Pytwitch:
    def __init__(self, token: str, channel: str):
        """
        Basic class for acquiring twitch chat messages.

        Args:
        token: OAuth token. Can be acquired at https://twitchapps.com/tmi/.
        channel: Target channel's name.
        """

        self.__sock = socket.socket()
        self.__CHAT_MSG = re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :")

        # Connect socket to Twitch
        self.__sock.connect(("irc.twitch.tv", 6667))

        # Authenticate and connect to channel over socket
        self.__sock.send("PASS {}\r\n".format(token).encode("utf-8"))
        self.__sock.send("NICK {}\r\n".format(channel).encode("utf-8"))
        self.__sock.send("JOIN {}\r\n".format(f'#{channel}').encode("utf-8"))

        # Avoids returning initial debug text
        self.get_message()
        self.get_message()
        self.get_message()

    def __check_connection(self, msg):
        # Respond to Twitch checking if the bot is still active
        if msg == "PING :tmi.twitch.tv\r\n":
            self.__sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            return True
        return False

    def get_message(self) -> str:
        """
        Returns the next chat message. Blocks until a message is received.
        """
        try:
            # Hangs until something is received
            message = self.__sock.recv(2048).decode("utf-8")

        except socket.error:
            return self.get_message()

        if self.__check_connection(message):
            return self.get_message()

        # Avoid AttributeError and TypeError
        if message:
            # Use regex to separate string
            username = re.search(r"\w+", message).group(0)
            message = self.__CHAT_MSG.sub("", message)

            # Force lowercase for fewer comparisons
            message = message.lower()

            # Remove invisible characters that mess with string comparison
            mapping = dict.fromkeys(range(32))
            clean_message = message.translate(mapping)

            return username, clean_message

    def close_socket(self):
        """
        Closes connection with the Twitch API.
        """
        self.__sock.close()


if __name__ == '__main__':
    chat = Pytwitch(open('keys/key_twitch.txt', 'r').read().strip(), 'aikochannel')

    while True:
        comment = chat.get_message()
        print('Got comment!')
        print(comment)

        if 'code red' in comment.lower():
            chat.close_socket()
            break

# ----------------------------------------------------------------------------
