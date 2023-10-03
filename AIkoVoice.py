"""
Voicelink.py

Handles voice related functionality such as text to speech and speech to text for Aiko's scripts.

File requirements:
- AIkoINIhandler.py >= 2.3

pip install:
- azure.cognitiveservices.speech
- keyboard

Changelog:

100:
- Organized functionality into classes.
110:
- Added "style" parameter to synthesizer's say method.
- Default style when no value is given is configurable.
- Default speech rate is now also configurable.
111:
- Recognizer class now uses event toggle instead of hotkey.
"""
import azure.cognitiveservices.speech as speechsdk
import subprocess
import keyboard
import time
from configparser import ConfigParser
from threading import Event


# reads config file
config = ConfigParser()
config.read('AIkoPrefs.ini')


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


class Recognizer:
    def __init__(self, microphone: str = config.get('VOICE', 'mic_device')):
        self.__set_speech_config()
        self.__set_audio_config(microphone)
        self.__set_speech_recognizer()
        self.__loop_started = False

    def __set_speech_config(self):
        # builds SpeechConfig class
        self.__speech_config = speechsdk.SpeechConfig(
        subscription = open('keys/key_azurespeech.txt', 'r').read().strip(),
        region = config.get('VOICE', 'azure_region')
            )

    def __set_audio_config(self, mic_device: str):
        # get the users chosen microphone device's endpoint id and builds AudioConfig class
        try:
            mic_id = get_device_endpoint_id(mic_device)
            self.__audio_config = speechsdk.audio.AudioConfig(
            use_default_microphone = False,
            device_name = mic_id
                )
        except:
            raise ValueError(f"Couldn't find entered microphone device's ID.")

    def __set_speech_recognizer(self):
        # builds SpeechRecognizer class
        self.__speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config = self.__speech_config,
        audio_config = self.__audio_config)

    def start(self, parse_func, event: Event):  # hotkey: str = config.get('LIVESTREAM', 'toggle_listening')
        self.__speech_recognizer.start_continuous_recognition()
        self.__speech_recognizer.recognized.connect(lambda evt: parse_func(evt))

        self.__loop_started = True
        is_recognizing = True

        while self.__loop_started:
            if event.is_set() and is_recognizing:  # keyboard.is_pressed(hotkey) and is_recognizing:
                self.__speech_recognizer.stop_continuous_recognition()
                is_recognizing = False
                print('\nPaused continuous speech recognition.\n')
                event.clear()
            elif event.is_set() and not is_recognizing:
                self.__speech_recognizer.start_continuous_recognition()
                print('\nResumed continuous speech recognition.\n')
                is_recognizing = True
                event.clear()
            time.sleep(0.1)

        print('\nDeactivated speech recognition.\n')

    def stop(self):
        self.__loop_started = False


class Synthesizer:
    def __init__(self, speakers: str = config.get('VOICE', 'audio_device'), voice: str = config.get('VOICE', 'azure_voice')):
        self.__set_speech_config()
        self.__set_audio_config(speakers)
        self.__set_speech_synthesizer()

        self.voice = voice
        self.default_style = config.get('VOICE', 'default_style')
        self.default_rate = config.getfloat('VOICE', 'default_rate')

    def __set_speech_config(self):
        # builds SpeechConfig class
        self.__speech_config = speechsdk.SpeechConfig(
        subscription = open('keys/key_azurespeech.txt', 'r').read().strip(),
        region = config.get('VOICE', 'azure_region')
        )

    def __set_audio_config(self, speakers: str):
        # get the users chosen device's endpoint id
        try:
            device_id = get_device_endpoint_id(speakers)
            default_speaker = False
        except:
            print(f"Couldn't find {speakers} audio device. Using default speakers.")
            device_id = ''
            default_speaker = True

        # builds AudioOutputConfig class
        self.__audio_config = speechsdk.audio.AudioOutputConfig(
            use_default_speaker=default_speaker,
            device_name=device_id
            )

    def __set_speech_synthesizer(self):
        # builds SpeechSynthesizer class
        self.__speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.__speech_config,
            audio_config=self.__audio_config
            )

    def say(self, text : str, rate : int = None, style : str = None):
        if rate == None:
            rate = self.default_rate
        if style == None:
            style = self.default_style

        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
        xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
            <voice name="{self.voice}">
                <mstts:express-as style="{style}" styledegree="2">
                    <prosody rate="{rate}">{text}</prosody>
                </mstts:express-as>
            </voice>
        </speak>"""

        speech_synthesis_result = self.__speech_synthesizer.speak_ssml_async(ssml).get()


if __name__ == '__main__':
    from threading import Thread

    event = Event()

    # tests synthesizer class
    synthesizer = Synthesizer()
    synthesizer.say('Hello there!')

    # sets up a function to be called on the speech_recognizer.recognized event
    def parse_event(evt):
        event = str(evt)

        keyword = 'text="'
        stt_start = event.index(keyword)
        stt_end = event.index('",')
        
        message = event[stt_start + len(keyword):stt_end]

        if message != '':
            print(message)

    recognizer = Recognizer()
    # to handle stopping the speech recognition.
    def stop_recognition_thread():
        while True:
            if keyboard.is_pressed('space'):
                event.set()


    # starts threads
    Thread(target=recognizer.start, kwargs={'parse_func': parse_event, 'event': event}).start()
    Thread(target=stop_recognition_thread).start()
