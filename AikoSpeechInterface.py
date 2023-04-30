"""
AikoSpeechInterface.py (former TextToSpeech.py)
Version 4.1

Library of text to speech functions for Aiko.

Requirements:

- mpg123 and ffmpeg installed and added to PATH

pip install:

- elevenlabslib
- pydub
- gtts
- speechrecognition
- pyaudio
- openai
- azure-cognitiveservices-speech

Changelog:
- Switched default text-to-speech method to Microsoft Azure Speech. Will default to GTTS if that fails.
- Rewrote push_to_talk function. Should no longer cause thread spam.
"""

import gtts                     # text to mp3 file
import os                       # to play audio file using mpg123
from pydub import AudioSegment  # to increase text-to-speech audio pitch
from elevenlabslib import *     # elevenlabs API python integration
import speech_recognition as sr # google speech-to-text
import openai                   # whisperAPI speech to text
import wave                     # to write .wav files
import pyaudio                  # to record audio
import keyboard                 # for push to talk hotkey
import azure.cognitiveservices.speech as speechsdk
from time import sleep

# sets some elevanlabs variables. optional
try:
    user = ElevenLabsUser(open("key_elevenlabs.txt", "r").read().strip('\n'))
    voice = user.get_voices_by_name("asuka-langley-yuko-miyamura")[0]
except Exception as e:
    print('Elevenlabs voice failed to start.')
    print('Error:', e)

# sets some azure speech variables. optional
try:
    speech_config = speechsdk.SpeechConfig(
    subscription=open("key_azurespeech.txt", "r").read().strip('\n'),
    region=open("key_region_azurespeech.txt", "r").read().strip('\n')
    )

    # voice type
    #"en-US-SaraNeural" #"en-US-NancyNeural" #"en-US-MichelleNeural" #"en-US-AmberNeural" #'en-US-AnaNeural' #'en-AU-CarlyNeural' #"en-GB-MaisieNeural"
    speech_config.speech_synthesis_voice_name = "en-US-SaraNeural"
except Exception as e:
    print('Azure Speech voice failed to start.')
    print('Error:', e)

# sets openAI API key. required for whisperAPI stt.
try:
    openai.api_key = open("key_openai.txt", "r").read().strip('\n')
except Exception as e:
    print('OpenAI API key failed to be set.')
    print('Error:', e)

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

def generate_tts_gtts(text : str, to_pitch_shift = False, pitch_shift = 1.0, tld = 'us', lang = 'en', slow = False):
    """Generates a text-to-speech mp3 file using google text to speech. Returns the name of the generated audio file.
    
    Parameters:
    text (str): The text to be synthesized.
    to_pitch_shift (bool): Whether to pitch shift or not. Defaults to False
    pitch_shift (float): The amount of semitones to raise/lower from the original voice tone. Defaults to 1.0
    tld (str): Accent for the chosen language. English ones are us, com.au, co.uk and co.in. Defaults to "us".
    lang (str): Language. 'en', 'pt', 'pt-br', etc. Defaults to "en".
    audiodevice (str): Which audio device to play the sound on. You'll want to set this to the number corresponding to your virtual cable device. Defaults to 1.
    slow (bool): Whether to speak slowly or not.
        """
    audio_file = "audio.mp3"
    gtts.gTTS(text, tld= tld, lang = lang, slow = slow).save(audio_file)

    if to_pitch_shift:
        modified_file = "mod_audio.mp3"
        modify_pitch(audio_file, modified_file, pitch_shift)
        os.remove(audio_file)
        return(modified_file)
    else:
        return(audio_file)

def generate_tts_elevenlabs(text):
    """Generates a text-to-speech mp3 file using elevenlabs API. Returns the name of the generated audio file.
     """

    audio_file = "audio.mp3"
    mp3_bytes = voice.generate_audio_bytes(prompt = text, stability = 0.75, similarity_boost = 0.75)

    with open(audio_file, "wb") as f:
        f.write(mp3_bytes)

    return(audio_file)

def generate_tts_azurespeech(text : str, to_pitch_shift = False, pitch_shift = 1.0):
    """
    Generates a speech audio file using Azure's text-to-speech service.

    Args:
    text (str): The text to be converted into speech.
    to_pitch_shift (bool): Whether or not to apply pitch shifting to the generated audio file.
    pitch_shift (float): The pitch shift factor to be applied to the audio file. Only applicable if to_pitch_shift is True.

    Returns:
    str: The filename of the generated audio file. If to_pitch_shift is True, the modified audio file's filename is returned instead.
    """
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    audio_file = "azuretts.wav"

    result = speech_synthesizer.speak_text_async(text).get()
    stream = speechsdk.AudioDataStream(result)
    stream.save_to_wav_file(audio_file)

    if to_pitch_shift:

        modify_pitch(audio_file, 'mod_azuretts.wav', pitch_shift)
        os.remove(audio_file)
        audio_file = 'mod_azuretts.wav'

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

def say(text: str, elevenlabs = False, audiodevice = "2"):
    """Generate text-to-speech audio and play it using `mpg123`.

    By default, the function uses Azure TTS to generate the audio. If that fails,
    it falls back to Google TTS. If the `elevenlabs` parameter is set to `True`,
    the function uses Elevenlabs TTS instead of Azure TTS.

    Args:
        text (str): The text to be spoken.
        elevenlabs (bool, optional): Whether to use Elevenlabs TTS or not.
            Defaults to False.
        audiodevice (str, optional): The audio device to be used by `mpg123`.
            Defaults to "2".
    """

    if elevenlabs:
        try:
            audio = generate_tts_elevenlabs(text)
            os.system(f"mpg123 -q --audiodevice {audiodevice} {audio}")
            os.remove(audio)
            return
        except Exception as e:
            print('Failed to generate elevenlabs tts.')
            print('Error:', e)
    # azure tts (currently broken)
    '''try:
        audio = generate_tts_azurespeech(text, True, 2.0)
        os.system(f"mpg123 -q --audiodevice {audiodevice} {audio}")
        os.remove(audio)
        return
    except Exception as e:
        print('Failed to generate Azure tts.')
        print('Error:', e)'''
    # google gtts
    try:
        audio = generate_tts_gtts(text, to_pitch_shift = True, pitch_shift = 2.0)
        os.system(f"mpg123 -q --audiodevice {audiodevice} {audio}")
        os.remove(audio)
        return
    except Exception as e:
        print('Failed to gtts tts.')
        print('Error:', e)

def start_push_to_talk(hotkey : str = 'num 0'):
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
        return stt
    except:
        return None

if __name__ == "__main__":
    
    # for testing push to talk
    hotkey = 'num 2'
    while True:
        if keyboard.is_pressed(hotkey):
            print(start_push_to_talk(hotkey))
            
        sleep(0.1)

    
    # for testing main tts function
    say('You are gay!')

    # for testing whisperAPI stt function

    #print(generate_stt_whisperAPI('recording.wav'))

    # for testing google speech recognition

    #print(listen('Listening...', 'hey'))

    # for testing audio devices

    #say("Hello Rchart-Kun! 1", audiodevice = 1)
    #say("Hello Rchart-Kun! 2", audiodevice = 2)
    #say("Hello Rchart-Kun! 3", audiodevice = 3)
    #say("Hello Rchart-Kun! 4", audiodevice = 4)

    # for testing elevenlabs voice

    #say("Hello Rchart-Kun!", elevenlabs=True)

    # to test push to talk