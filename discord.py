'''
Instructions:

- Make a discord account for your AI character.
- On your character's account, go to discord's 'voice and video' settings tab.
- Set the discord input device to your virtual cable/voice mod microphone.
- Set the discord output device to a second virtual cable.
- In this script, change the string 'CABLE-B Output' to whatever your second virtual cable is named.
- Join a voice chat using your character's account.
- Run this script.

If you follow these steps correctly, you should be able to talk to your AI character on a discord voice chat from your
own account.
'''
import keyboard
from AIko import AIko
from time import sleep
from threading import Thread, Lock
from Streamlab import MessageContainer
from VoiceLink import Synthesizer, Recognizer

charname = 'Aiko'
# SET SECOND VIRTUAL CABLE HERE
recognizer = Recognizer('CABLE-B Output')

message = MessageContainer()

# --------
def parse_event(evt):
    global message

    event = str(evt)

    keyword = 'text="'
    stt_start = event.index(keyword)
    stt_end = event.index('",')
    
    result = event[stt_start + len(keyword):stt_end]

    if result != '':
        message.switch_message(f'Voice-chat: {result}')
# ---------
# threads
running = True
def retrieve_message():
    global running, message, charname

    Aiko = AIko(charname, f'prompts/{charname}.txt')
    synthesizer = Synthesizer()
    output = ''

    while True:
        if not running:
            break
        if message.has_message:
            prompt = message.get_message()
            if prompt != '':
                print(prompt)

                output = Aiko.interact(prompt)
                print(f'{charname}: {output}')
                synthesizer.say(output)

        sleep(0.01)

def wait_for_end(hotkey: str = 'del'):
    global recognizer, running
    
    keyboard.wait(hotkey)
    running = False
    recognizer.stop()

# starts threads
Thread(target = recognizer.start, kwargs = {'parse_func': parse_event}).start()
Thread(target = retrieve_message).start()
Thread(target = wait_for_end).start()

print('All threads started.\n')