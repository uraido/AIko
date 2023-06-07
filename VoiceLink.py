import os
import azure.cognitiveservices.speech as speechsdk
import subprocess
from configparser import ConfigParser
import os

if __name__ == '__main__':
    from AikoINIhandler import handle_ini
    handle_ini()

# reads config file
config = ConfigParser()
config.read('AikoPrefs.ini')

# sets variables according to config
audio_device = config.get('VOICE', 'audio_device')
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
    default_speaker = True

# builds AudioOutputConfig class
audio_config = speechsdk.audio.AudioOutputConfig(
    use_default_speaker=default_speaker,
    device_name=device_id
    )

# sets the voice
speech_config.speech_synthesis_voice_name = azure_voice #'en-AU-CarlyNeural' #'en-GB-MaisieNeural' #'en-US-AnaNeural'

def say(text : str):
    global speech_config
    global audio_config

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

if __name__ == '__main__':
    say('Hello there!')