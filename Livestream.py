"""
GUI interaction loop for livestreaming.

Requirements:

.py:
- AIko.py (159beta or greater) and its requirements.
- AIkoINIHandler.py (24 or greater).
- AIkoGUITools.py (015 or greater).
- AIkoStreamingTools.py (029 or greater).
- AIkoVoice.py (115 or greater) and its requirements.

packages:
- pip install pytchat

Changelog:

001:
- Initial release.
002:
- Renamed some commands and added descriptions for better clarity.
003:
- Added follower alerts through parsing StreamElements chat alerts.
004:
- Renamed spontaneous messages feature to silence breaker.
- Silence breaker only triggers after a random amount of silence.
005:
- Reorganized thread_twitch_chat function into a class.
- Reorganized thread_chat_youtube function into a class.
006:
- Reorganized YouTube and Twitch chat loop classes into a single class.
- Added mute, chat_pause and chat_clear commands.
007:
- Skips user mentions (unless mentioning Aiko herself)
008:
- Updated to work with AIko.py 159beta.
009:
- Added debug_fom command, which enables FOM printouts (current score, current mood).
010:
- Added local READ_ONLY keyword to system messages. Character will read the message, then save it as a side prompt.
"""
import os
import socket
from time import sleep, time
from threading import Thread, Event
from configparser import ConfigParser
from random import choice, uniform, randint

import pytchat

from AIko import AIko, txt_to_list
from AIkoGUITools import LiveGUI
from AikoINIhandler import handle_ini
from AIkoVoice import Synthesizer, Recognizer
from AIkoStreamingTools import MasterQueue, Pytwitch
build = '009'

handle_ini()

# main objects
aiko = AIko('Aiko', 'prompts/AIko.txt')
master_queue = MasterQueue()
app = LiveGUI(master_queue, aiko)

# config
config = ConfigParser()
config.read('AikoPrefs.ini')

# loop controller
running = True

# threading events
mute_event = Event()
allow_silence_breaker = Event()
speaking = Event()

# globals
debug_fom = False

# time tracker (to track silence time)
last_time_spoken = time()
# ---------------------------------------- COMMAND LINE COMMAND FUNCTIONS ----------------------------------------------


def cmd_toggle_mic():
    mute_event.set()


# first, sets the function to be called when the mute button is pressed
app.bind_mute_button(cmd_toggle_mic)
# then adds a mute/un-mute command which invokes the button
app.add_command('mute', app.bp_button_mute.press, 'Mutes/un-mutes the microphone.')


def cmd_help():
    app.print_to_cmdl()


def cmd_start_silence_breaker():
    global last_time_spoken

    last_time_spoken = time()
    allow_silence_breaker.set()
    app.print_to_cmdl('Started the silence breaker.')


app.add_command('sb_start', cmd_start_silence_breaker, 'Starts the silence breaker.')


def cmd_stop_silence_breaker():
    allow_silence_breaker.clear()
    app.print_to_cmdl('Stopped the silence breaker.')


app.add_command('sb_stop', cmd_stop_silence_breaker, 'Stops the silence breaker.')


def cmd_check_spontaneous():
    if allow_silence_breaker.is_set():
        app.print_to_cmdl('Silence breaker is currently: UNPAUSED.')
    else:
        app.print_to_cmdl('Silence breaker is currently: PAUSED.')


app.add_command('sb_check', cmd_check_spontaneous, 'Checks silence breaker status.')


def cmd_switch_scenario(scenario: str):
    aiko.change_scenario(scenario)
    app.print_to_cmdl('Changed scenario.')


app.add_command('scenario_change', cmd_switch_scenario, 'Changes the current scenario.')


def cmd_check_scenario():
    scenario = aiko.check_scenario()
    if scenario == '':
        scenario = 'NO SCENARIO'
    app.print_to_cmdl(f'Current scenario: "{scenario}"')


app.add_command('scenario_check', cmd_check_scenario, 'Prints the current scenario.')


def cmd_add_side_prompt(side_prompt: str):
    aiko.add_side_prompt(side_prompt)
    app.update_side_prompts_widget()

    app.print_to_cmdl(f'Added local SP: "{side_prompt}"')


app.add_command('sp_add', cmd_add_side_prompt, "Injects a side-prompt into the character's memory.")


def cmd_clear_side_prompts():
    for i in range(0, 5):
        aiko.context.side_prompts.delete_item(i)

    app.update_side_prompts_widget()
    app.print_to_cmdl('Cleared all side prompts.')


app.add_command('sp_clear', cmd_clear_side_prompts, 'Deletes all side-prompts.')


def cmd_send_sys_message(message: str):
    master_queue.add_message(message, "system")
    app.print_to_cmdl(f'Added SM to queue: "{message}"')


app.add_command('send_sys_msg', cmd_send_sys_message, 'Sends a system message to be immediately answered by the char.')


def cmd_chat_clear():
    app.chat_button_pause.press()
    for i in range(0, 10):
        master_queue.delete_chat_message(i)
    app.chat_button_pause.press()
    app.print_to_cmdl('Clearing chat messages...')


app.add_command('chat_clear', cmd_chat_clear, 'Clears all chat messages currently in queue.')


def cmd_chat_pause():
    app.chat_button_pause.press()
    app.print_to_cmdl('Paused/un-paused the chat queue.')


app.add_command('chat_pause', cmd_chat_pause, 'Pauses/unpauses the chat queue.')


def cmd_debug_fom(debug: str):
    global debug_fom
    debug_fom = bool(debug.capitalize())
    app.print_to_cmdl(f'Set debug_fom to {debug.upper()}.')


app.add_command('debug_fom', cmd_debug_fom,
                'Enables FrameOfMind feature debugging printouts. Usage: debug_fom true/false')


def cmd_close_protocol():
    global running

    running = False
    app.close_app()
    os._exit(0)


app.add_command('exit', cmd_close_protocol, 'Closes the app.')
# also sets this function to run when the app is closed

app.set_close_protocol(cmd_close_protocol)


# ------------------------------------- THREADED LOOP CLASSES / FUNCTIONS ----------------------------------------------

class ChatLoop:
    def __init__(self, queue: MasterQueue, ui_app: LiveGUI, youtube: bool = False, yt_id: str = None):
        self.__queue = queue
        self.__app = ui_app

        if youtube:
            self.__chat = pytchat.create(video_id=yt_id)
            self.__loop = self.__loop_youtube
        else:
            self.__loop = self.__loop_twitch

        self.__running = False

    def start(self):
        self.__running = True
        Thread(target=self.__loop).start()

    def stop(self):
        self.__running = False

    def __skip_message(self, message, author):
        # skips chat commands
        if message[0] == '!':
            return True

        if '@' in message:
            if 'aikochannel' in message:
                pass
            else:
                return True

        # parses follow alerts and sends them as system messages
        if author.lower() == 'streamelements' and 'just followed!' in message.lower():
            follower = message.split(" ", 1)[0][1:]
            self.__queue.add_message(
                f'EVENT: {follower} just followed you on Twitch. Thank them! Read their name!', "system")
            self.__app.print_to_cmdl(f'{follower} just followed. Letting the character know...')
            return True

        # skips bot replies
        if author.lower() == 'streamelements':
            return True

        return False

    def __attempt_merge(self, message, author):
        if author == self.__last_author:
            merged_message = f'{self.__last_message} {message}'
            try:
                self.__queue.edit_chat_message(self.__last_message, merged_message)
                self.__app.print_to_cmdl(f'Merge triggered: {self.__last_message} + {message}')
                self.__last_message = merged_message

                self.__app.update_chat_widget()
                return True
            except ValueError:
                self.__app.print_to_cmdl('Attempted a message merge, but exception occurred.')
                return False

    def __loop_twitch(self):
        # starts pytwitch object
        chat = Pytwitch(open('keys/key_twitch.txt').read().strip(), "aikochannel")
        # last author variable for merging messages
        self.__last_author = None

        while running:
            # blocks until a message is received
            author, message = chat.get_message()
            # checks whether message should be skipped (bot commands, etc)
            if self.__skip_message(message, author):
                continue
            # merges current message with last message if the same user immediately follows up with a second message
            if self.__attempt_merge(message, author):
                continue

            self.__last_author = author
            self.__last_message = f'{self.__last_author}: {message}'

            # adds message to queue
            self.__queue.add_message(self.__last_message, "chat")

            self.__app.update_chat_widget()

            # to keep CPU usage from maxing out
            sleep(0.1)

    def __loop_youtube(self):
        self.__last_author = None

        while self.__chat.is_alive():
            if not running:
                break
            for c in self.__chat.get().sync_items():
                if not running:
                    break
                # merges current message with last message if the same user immediately follows up with a second message
                if self.__attempt_merge(c.message, c.author.name):
                    continue

                self.__last_author = c.author.name
                self.__last_message = f'{self.__last_author}: {c.message}'

                # adds message to queue
                self.__queue.add_message(self.__last_message, "chat")

                self.__app.update_chat_widget()

            # to keep CPU usage from maxing out
            sleep(0.1)


def thread_remote_receiver():
    global running
    # ------------ Set Up ----------------
    # server_ip = '26.124.79.180'    # Ulaidh's ID (FOR RCHART TO USE)
    # server_ip = '26.246.74.120'    # Rchart's ID (FOR ULAIDH TO USE)
    # port = 5004
    server_ip = config.get('REMOTE_SIDE_PROMPTING', 'server_ip')
    port = config.getint('REMOTE_SIDE_PROMPTING', 'port')
    # ------------------------------------

    while running:

        try:
            # ------- TCP IP protocol -------
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((server_ip, port))
            msg = s.recv(1024)
            # -------------------------------

            message = msg.decode()[:-1]
            completion_option_selected = msg.decode()[-1]
            app.print_to_cmdl(
                f'Remote side prompt received with the option {completion_option_selected}: {message}'
                )

            if completion_option_selected == '1':
                master_queue.add_message(message, "system")

            elif completion_option_selected == '2':
                aiko.add_side_prompt(message)
                app.update_side_prompts_widget()

            else:
                app.print_to_cmdl('Remote side prompt received but something went wrong. Side prompt ABORTED!')

            # disconnect the client
            s.close()
        except:
            pass
        sleep(0.1)


def thread_speech_recognition():
    username = config.get('GENERAL', 'username')

    def parse_event(evt):
        event = str(evt)

        keyword = 'text="'
        stt_start = event.index(keyword)
        stt_end = event.index('",')

        message = event[stt_start + len(keyword):stt_end]

        if message != '':
            master_queue.add_message(f'{username}: {message}', "mic")
            app.print_to_cmdl(f'Added mic message to queue: {message}')

    # creates recognizer object for speech recognition
    recognizer = Recognizer()

    mute_event.wait()
    mute_event.clear()
    # print('\nEnabled speech recognition.\n')
    sleep(0.1)

    recognizer.start(parse_event, mute_event)


def thread_silence_breaker():
    global last_time_spoken
    system_prompts = txt_to_list('prompts\spontaneous_messages.txt')
    generic_messages = txt_to_list('prompts\generic_messages.txt')

    min_time = config.getint('SPONTANEOUS_TALKING', 'min_time')
    max_time = config.getint('SPONTANEOUS_TALKING', 'max_time')

    # rolls initial max silence time
    max_silence_time = randint(min_time, max_time)

    while running:
        # to save on CPU usage during loop execution
        sleep(0.1)
        # executes if spontaneous messages arent paused (paused by default)
        if not allow_silence_breaker.is_set():
            continue
        # also checks if the character is currently speaking before continuing
        if speaking.is_set():
            continue

        # checks if time threshold has been reached
        now = time()
        if not now - last_time_spoken >= max_silence_time:
            continue
        # re-rolls max silence time
        max_silence_time = randint(min_time, max_time)
        # decides between spontaneous or generic message
        dice = randint(0, 1)
        if dice == 0:
            try:
                message = system_prompts.pop(randint(0, len(system_prompts) - 1))
                master_queue.add_message(message, "system")
                sleep(randint(min_time, max_time))
                continue
            except:
                pass

        # if dice == 1
        master_queue.add_message(choice(generic_messages), "system")


def thread_talk():
    global last_time_spoken

    # to parse messages before voicing
    def parse_msg(msg: str, character: str = ':', after=False):

        if after:
            return msg[msg.index(character) + 2:]

        return msg[: msg.index(character)]

    # creates synthesizer object to voice Aiko
    synthesizer = Synthesizer()

    # creates/clears text file to display message author's name in OBS
    with open('message_author.txt', 'w') as txt:
        pass

    while True:
        msg_type, message = master_queue.get_next()
        if msg_type == 'chat':
            app.update_chat_widget()

        # READ_ONLY keyword
        elif msg_type == 'system' and message.startswith('READ_ONLY:'):
            message = message.strip('READ_ONLY:')
            synthesizer.say(message, rate=(uniform(1.2, 1.4)))
            aiko.add_side_prompt(message)
            app.update_side_prompts_widget()
            continue

        # no messages in queue
        if message == '':
            continue

        output = aiko.interact(message, use_system_role=msg_type == "system")

        # reads message before answering, if message is a chat message.
        if msg_type == 'chat':
            # writes message author's name to text file to display in OBS
            with open('message_author.txt', 'w') as txt:
                txt.write('Now reading:\n')
                txt.write(f"{parse_msg(message, after=False).upper()}'s message")

            synthesizer.say(parse_msg(message, after=True), rate=uniform(1.2, 1.4), style="neutral")

        app.print(f'({msg_type.upper()}) {message}')
        app.print(f'Aiko: {output}\n')

        # FOM debug printouts
        if debug_fom:
            app.print(f'CURRENT SCORE: {aiko.fom.check_score()}')
            app.print(f'NEXT MOOD: {aiko.context.check_personality()}\n')

        speaking.set()
        synthesizer.say(output)
        speaking.clear()
        # resets timer
        last_time_spoken = time()

        with open('message_author.txt', 'w') as txt:
            pass

        sleep(0.1)

# ----------------------------------------------------------------------------------------------------------------------


platform = config.get('LIVESTREAM', 'platform').lower()

chat_loop = ChatLoop(master_queue, app, platform == 'youtube', config.get('LIVESTREAM', 'liveid'))
chat_loop.start()

Thread(target=thread_remote_receiver).start()
Thread(target=thread_speech_recognition).start()
Thread(target=thread_silence_breaker).start()
Thread(target=thread_talk).start()
app.print_to_cmdl('All threads started.')
app.print_to_cmdl(f'Running AILiveGUI build {build}. Type "help" to see commands.')
app.run()
