"""
Voicelink.py

Handles voice related functionality such as text to speech and speech to text for Aiko's scripts.

File requirements:
- AikoINIhandler.py >= 1.5

pip install:
- azure.cognitiveservices.speech
- keyboard

Changelog:

050:
- Removed option to use default mic, since that caused a bug which caused AIko to 'hear' herself and be stuck in a loop
answering herself. User must specify a microphone device to use speech_recognition.
051:
- Exception printout when getting microphone device is now more specific.
- Removed leftover use_default_mic setting import that caused an error.
052:
- Now generates captions.txt file for displaying subtitles.
"""
import os
import azure.cognitiveservices.speech as speechsdk
import subprocess
import keyboard
import time
from configparser import ConfigParser
from threading import Thread, Event

if __name__ == '__main__':
    from AikoINIhandler import handle_ini
    handle_ini()

# reads config file
config = ConfigParser()
config.read('AikoPrefs.ini')

# sets variables according to config
audio_device = config.get('VOICE', 'audio_device')
mic_device = config.get('VOICE', 'mic_device')
azure_voice = config.get('VOICE', 'azure_voice')
azure_region = config.get('VOICE', 'azure_region')

def get_device_endpoint_id(device : str):
    sd = subprocess.run(
        ["pnputil", "/enum-devices", "/connected", "/class", "AudioEndpoint"],
        capture_output=True,
        text=True,
    )

    device_info = sd.stdout.split("\n")[1:-1]

    found_curly = False

    virtual_cable_device_id = ''

    for line in range(len(device_info)):
        if device.lower() in device_info[line + 1].lower():
            for letter in device_info[line]:
                if letter == '{':
                    found_curly = True
                if found_curly:
                    virtual_cable_device_id += letter
            break

    return(virtual_cable_device_id)

# builds SpeechConfig class
speech_config = speechsdk.SpeechConfig(
    subscription=open("keys/key_azurespeech.txt", "r").read().strip('\n'), 
    region='brazilsouth'
    )

# get the users chosen device's endpoint id
try:
    device_id = get_device_endpoint_id(audio_device)
    default_speaker = False
except:
    print(f"Couldn't find {audio_device} audio device. Using default speakers.")
    device_id = ''
    default_speaker = True

# builds AudioOutputConfig class
audio_config = speechsdk.audio.AudioOutputConfig(
    use_default_speaker=default_speaker,
    device_name=device_id
    )

# sets the voice
speech_config.speech_synthesis_voice_name = azure_voice #'en-AU-CarlyNeural' #'en-GB-MaisieNeural' #'en-US-AnaNeural'

# builds SpeechSynthesizer class
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

def generate_captions(text : str, done_event : Event):
    with open('captions.txt', 'w') as captions:
        pass

    for letter in text:
        with open('captions.txt', 'a') as captions:
            captions.write(letter)
        time.sleep(0.05)
    done_event.wait()
    
    with open('captions.txt', 'w') as captions:
        pass

def say(text : str):
    global speech_synthesizer

    done_event = Event()

    Thread(target = generate_captions, kwargs = {'text': text, 'done_event': done_event}).start()
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

    done_event.set()

# get the users chosen microphone device's endpoint id and builds AudioConfig class
try:
    mic_id = get_device_endpoint_id(mic_device)
    input_config = speechsdk.audio.AudioConfig(
    use_default_microphone=False,
    device_name=mic_id
        )
except:
    raise(f"Couldn't find {mic_device} input device.")

# builds SpeechRecognizer class
speech_recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config,
    audio_config=input_config)

# sets variable for handling speech recognizing loop
recognition_activated = False

def start_speech_recognition(parse_func, hotkey : str = 'Page Up'):
    """
    Starts continuous speech recognition using Azure Speech to Text.

    Parameters:
    - hotkey (str): The hotkey to toggle speech recognition on/off. Default is 'Page Up'.
    - parse_func: The function to parse and handle recognized speech events.

    Usage:
    - Make sure to call this function in a threaded environment for reliable control over the while loop.
    - To stop the continuous recognition, you can call the stop_continuous_recognition() function from another thread.
    """
    global recognition_activated
    global speech_recognizer

    recognition_activated = True

    speech_recognizer.start_continuous_recognition()
    speech_recognizer.recognized.connect(lambda evt: parse_func(evt))

    is_recognizing = True

    while recognition_activated:
        if keyboard.is_pressed(hotkey) and is_recognizing:
            speech_recognizer.stop_continuous_recognition()
            is_recognizing = False
            print('\nPaused continuous speech recognition.\n')
        elif keyboard.is_pressed(hotkey) and not is_recognizing:
            speech_recognizer.start_continuous_recognition()
            print('\nResumed continuous speech recognition.\n')
            is_recognizing = True
        time.sleep(0.1)

def stop_speech_recognition():
    global recognition_activated

    recognition_activated = False
    print('\nDeactivated speech recognition.\n')

if __name__ == '__main__':
    from VoiceLink import start_speech_recognition, stop_speech_recognition
    from threading import Thread

    # tests say function
    say('Hello there!')

    # sets up a function to be called on the speech_recognizer.recognized event
    def parse_event(evt):
        event = str(evt)

        keyword = 'text="'
        stt_start = event.index(keyword)
        stt_end = event.index('",')
        
        message = event[stt_start + len(keyword):stt_end]

        if message != '':
            print(message)

    # to test speech recognition. started in a thread.
    def speech_recognition_thread():
        start_speech_recognition(parse_func = parse_event)

    # to handle stopping the speech recognition.
    def stop_recognition_thread():
        keyboard.wait('space')
        stop_speech_recognition()

    # starts threads
    Thread(target=speech_recognition_thread).start()
    Thread(target=stop_recognition_thread).start()