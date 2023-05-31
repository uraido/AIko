"""
AikoSpeechInterface.py (former TextToSpeech.py)
Version 5.0

Library of text to speech functions for Aiko.

Requirements:

- mpg123 and ffmpeg installed and added to PATH
- AikoINIhandler.py

pip install:

- elevenlabslib
- pydub
- gtts
- speechrecognition
- pyaudio
- openai
- azure-cognitiveservices-speech

txt files:

- key_azurespeech.txt
- key_region_azurespeech.txt
- key_elevenlabs.txt (optional)

Changelog:
050:
- Implemented .ini configuration file.
- Text to speech synthesizing functions no longer have a pitch shift parameter. Pitch shift is now controlled by the
say() function.
- If azure or elevenlabs text to speech fail to start, the speech method is set to GTTS to avoid error message spam
when calling the say() function.
- Rewrote say() function for better exception handling.
0501:
- Added AIkoINIhandler.py as a dependency.
051:
- Further improved say() function exception handling.
052:
- Say() function now writes its "text" parameter to a txt file, allowing software like OBS to display
captions.
053:
- Added general use play() function to play any audio files using mpg123.
- say() function now use the play() function to play the audio.
"""

print('AikoSpeechInterface.py: Starting...')
print()

if __name__ == '__main__':
    from AikoINIhandler import handle_ini
    handle_ini()

import gtts                                         # text to mp3 file
import os                                           # to play audio file using mpg123
from pydub import AudioSegment                      # to increase text-to-speech audio pitch
from elevenlabslib import *                         # elevenlabs tts API python integration
import speech_recognition as sr                     # google speech-to-text
import openai                                       # whisperAPI speech to text
import wave                                         # to write .wav files
import pyaudio                                      # to record audio
import keyboard                                     # for push to talk hotkey
import azure.cognitiveservices.speech as speechsdk  # azure API text to speech
from configparser import ConfigParser               # configuration file
from time import sleep                              # ???

# reads config file
config = ConfigParser()
config.read('AikoPrefs.ini')

# sets variables according to config
audio_device = config.getint('SPEECH_INTERFACE', 'audio_device')
tts_method = config.get('SPEECH_INTERFACE', 'tts_method')
elevenlabs_voice = config.get('SPEECH_INTERFACE', 'elevenlabs_voice')
azure_voice = config.get('SPEECH_INTERFACE', 'azure_voice')
azure_region = config.get('SPEECH_INTERFACE', 'azure_region')
pitch_shift = config.getfloat('SPEECH_INTERFACE', 'pitch_shift')

# attempts to starts elevenlabs tts, if set in the config
if tts_method == 'elevenlabs':
    try:
        user = ElevenLabsUser(open("keys/key_elevenlabs.txt", "r").read().strip('\n'))
        voice = user.get_voices_by_name(elevenlabs_voice)[0]
    except Exception as e:
        tts_method = 'gtts'

        print('AikoSpeechInterface:')
        print('Elevenlabs voice failed to start.')
        print('Error:', e)
        print('Defaulted TTS method to GTTS.')
        print()

# attempts to starts azure tts, if set in the config
elif tts_method == 'azure':
    try:
        speech_config = speechsdk.SpeechConfig(
        subscription=open("keys/key_azurespeech.txt", "r").read().strip('\n'),
        region=azure_region
        )

        # voice type
        speech_config.speech_synthesis_voice_name = azure_voice
    except Exception as e:
        tts_method = 'gtts'

        print('AikoSpeechInterface:')
        print('Azure Speech voice failed to start.')
        print('Error:', e)
        print('Defaulted TTS method to GTTS.')
        print()

# acknowledges GTTS
elif tts_method == 'gtts':
    pass

# defaults to GTTS if invalid method is selected
else:
    print('AikoSpeechInterface:')
    print(f'Invalid speech method selected: {tts_method}')
    print('Defaulting to GTTS.')
    print()

# attempts to set openAI API key. required for whisperAPI TTS
try:
    openai.api_key = open("keys/key_openai.txt", "r").read().strip('\n')
except Exception as e:
    print('AikoSpeechInterface:')
    print('OpenAI API key failed to be set.')
    print('Error:', e)
    print()

def modify_pitch(input_file, output_file, pitch_shift):
    """
    Modifies the pitch of an audio file and saves the modified audio to a new file.

    Parameters:
        input_file (str): The path to the input audio file.
        output_file (str): The path to the output audio file.
        pitch_shift (int): The amount of pitch shift in semitones (positive for higher pitch, negative for lower pitch).

    Returns:
        None
    """
    # Load the audio file
    song = AudioSegment.from_file(input_file)

    # Shift the pitch
    shifted_song = song._spawn(song.raw_data, overrides={
        "frame_rate": int(song.frame_rate * (2.0 ** (pitch_shift / 12.0)))
    })
    shifted_song = shifted_song.set_frame_rate(song.frame_rate)

    # Export the shifted audio
    shifted_song.export(output_file, format="mp3")

    # Removes original file
    os.remove(input_file)

def generate_tts_gtts(text : str, tld = 'us', lang = 'en', slow = False):
    """Generates a text-to-speech mp3 file using google text to speech. Returns the name of the generated audio file.
    
    Parameters:
    text (str): The text to be synthesized.
    to_pitch_shift (bool): Whether to pitch shift or not. Defaults to False
    tld (str): Accent for the chosen language. English ones are "us", "com.au", "co.uk" and "co.in". Defaults to "us".
    lang (str): Language. 'en', 'es', 'pt-br', etc. Defaults to "en".
    slow (bool): Whether to speak slowly or not.
        """
    audio_file = "gtts_audio.mp3"
    gtts.gTTS(text, tld = tld, lang = lang, slow = slow).save(audio_file)

    return(audio_file)

def generate_tts_elevenlabs(text):
    """Generates a text-to-speech mp3 file using elevenlabs API. Returns the name of the generated audio file.
     """

    audio_file = "elevenlabs_audio.mp3"
    mp3_bytes = voice.generate_audio_bytes(prompt = text, stability = 0.75, similarity_boost = 0.75)

    with open(audio_file, "wb") as f:
        f.write(mp3_bytes)

    return(audio_file)

def generate_tts_azurespeech(text : str):
    """
    Generates a speech audio file using Azure's text-to-speech service.

    Args:
    text (str): The text to be converted into speech.

    Returns:
    str: The filename of the generated audio file.
    """
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    audio_file = "azuretts.wav"

    result = speech_synthesizer.speak_text_async(text).get()
    stream = speechsdk.AudioDataStream(result)
    stream.save_to_wav_file(audio_file)

    return audio_file

def generate_stt_whisperAPI(filename : str):
    """
    Generates a transcript of the speech audio file using OpenAI's whisper-1 speech-to-text API.

    Args:
    filename (str): The filename of the speech audio file.

    Returns:
    str: The transcript of the speech audio file.
    """
    audio_file = open(filename, "rb")
    transcript = openai.Audio.transcribe(model = "whisper-1", file = audio_file, language="en", fp16=False, verbose=True, initial_prompt='code red')

    return(transcript.text)

def listen(prompt='', catchword=''):
    """
    Uses SpeechRecognition library to listen to audio input from a microphone and convert any speech it detects to text using 
    Google's speech recognition API. Returns the recognized text as a string or None if no speech is detected. 
    
    Parameters:
    prompt (str): Optional prompt text to print to the console before listening for audio input.
    catchword (str): Optional catchword that specifies a particular word or phrase that should be included at the very 
    beginning of the recognized text. If provided, the function will only return text that includes the catchword at the 
    beginning. 
    
    Returns:
    str or None: The recognized text as a string, or None if no speech is detected that meets the specified catchword 
    criteria.
    """

    r = sr.Recognizer()
    text = None

    if prompt != '':
        print(prompt)

    try:    
        with sr.Microphone() as source:
            audio = r.listen(source)
            microphone_output = r.recognize_google(audio)
        if catchword == '':
            text = microphone_output
        elif catchword.lower() in microphone_output[:len(catchword)].lower():
            text = microphone_output

    except sr.exceptions.UnknownValueError:
        pass

    return text 

def say(text: str, method : str = tts_method, pitch_shift : float = pitch_shift):
    """Generate text-to-speech audio and play it using `mpg123`.

    By default, the function uses Azure TTS to generate the audio. If that fails,
    it falls back to Google TTS. If the `elevenlabs` parameter is set to `True`,
    the function uses Elevenlabs TTS instead of Azure TTS.
    Also saves text parameter into a .txt file (captions.txt) so it can be used to generate captions
    when using software such as OBS.

    Args:
        text (str): The text to be spoken.
        method (str, optional): Which text to speech method to use.
            Defaults to config file.
        pitch_shift (float, optional): The amount of pitch shift to apply in semitones.
            Defaults to config file.
    """
    tts_exception = False

    # writes said text to txt file so OBS can read it to display it on screen
    with open('captions.txt', 'w') as captions:
        captions.write(text)

    # synthesizes text to speech using selected method (azure, elevenlabs)
    try:

        if tts_method == 'elevenlabs':
            audio = generate_tts_elevenlabs(text)
        elif tts_method == 'azure':
            audio = generate_tts_azurespeech(text)

    # catches exceptions and sets exception flag
    except Exception as e:

        tts_exception = True

        print('AikoSpeechInterface.py:')
        print(f'Failed to generate {tts_method} tts.')
        print('Error:', e)
        print('Defaulting to gtts...')
        print()

    # synthesizes text to speech using GTTS if GTTS method is selected or if the selected method failed
    if tts_method == 'gtts' or tts_exception:

        try:
            audio = generate_tts_gtts(text)
        except Exception as e:
            
            print('AikoSpeechInterface.py:')
            print(f'Failed to generate GTTS tts.')
            print('Error:', e)
            print()

    
    # applies pitch shift, if appliable
    try:
        if pitch_shift > 0:
            modify_pitch(audio, 'mod_audio.wav', pitch_shift)
            audio = 'mod_audio.wav'
    except Exception as e:
        print('AikoSpeechInterface.py: Error modifying pitch')
        print(e)
        print()

    # plays audio file then removes it
    play(audio)
    os.remove(audio)

    # removes captions file after audio is done playing
    os.remove('captions.txt')

def start_push_to_talk(hotkey : str = 'num 0'):
    """
    Records audio while a hotkey is pressed and transcribes the resulting
    audio to text using the Whisper API. Returns the transcribed text, or
    an empty string if transcription failed.

    Args:
        hotkey (str): The hotkey to use for recording audio (default: 'num 0').

    Returns:
        str: The transcribed text from the recorded audio, or an empty string
             if transcription failed.
    """
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100
    WAVE_OUTPUT_FILENAME = "output.wav"

    p = pyaudio.PyAudio()
    frames = []
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Recording...")

    while keyboard.is_pressed(hotkey):
        data = stream.read(CHUNK)
        frames.append(data)

    print("Done recording.")

    stream.stop_stream()
    stream.close()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    try:
        stt = generate_stt_whisperAPI(WAVE_OUTPUT_FILENAME)
        os.remove(WAVE_OUTPUT_FILENAME)
        return stt
    except Exception as e:
        print('AikoSpeechInterface.py:')
        print(f'Could not transcribe push to talk: {e}')
        print()
        return ''

def play(audio_filename : str, audiodevice : int = audio_device):
    """
    Plays an audio file using the mpg123 command-line tool.

    Args:
        audio_filename (str): The path to the audio file to be played.
        audiodevice (int, optional): The audio device ID to be used for playback. Defaults to audio_device.

    Returns:
        bool: True if the audio is played successfully, False otherwise.

    Raises:
        Exception: If there is an error playing the audio.

    Example:
        >>> play("audio.mp3", audiodevice=2)
        True
    """
    try:
        # plays audio file
        os.system(f"mpg123 -q --audiodevice {audiodevice} {audio_filename}")
        return True
    except Exception as e:
        print('AikoSpeechInterface.py: Error playing audio')
        print(e)
        print()
        return False

if __name__ == "__main__":
    # for testing audio devices
    for device in range(0, 5):
        audio = generate_tts_gtts(str(device))
        play(audio, device)
        os.remove(audio)
    # ------------------------------