'''
Instructions:

- Make a discord account for your AI character.
- On your character's account, go to discord's 'voice and video' settings tab.
- Set the discord input device to your virtual cable/voice mod microphone.
- Set the discord output device to a second virtual cable.
- In this script, change the string 'CABLE-B Output' to whatever your second virtual cable is named.
- Join a voice chat using your character's account.
'''
import keyboard
from AIko import AIko
from threading import Thread
from VoiceLink import Synthesizer, Recognizer

# SET SECOND VIRTUAL CABLE HERE
recognizer = Recognizer('CABLE-B Output')

# --------
Aiko = AIko('Aiko', 'prompts/Aiko.txt')
synthesizer = Synthesizer()

def parse_event(evt):
    global Aiko, synthesizer
    event = str(evt)

    keyword = 'text="'
    stt_start = event.index(keyword)
    stt_end = event.index('",')
    
    result = event[stt_start + len(keyword):stt_end]

    if result != '':
        print(f'User: {result}\n')
        output = Aiko.interact(f'Voice-chat: {result}')
        print(f'Aiko: {output}\n')
        synthesizer.say(output)
# ---------
# threads
def wait_for_end(hotkey: str = 'del'):
    global recognizer
    
    keyboard.wait(hotkey)
    recognizer.stop()

# starts threads
Thread(target = recognizer.start, kwargs = {'parse_func': parse_event}).start()
Thread(target = wait_for_end).start()

print('All threads started.\n')