"""
AikoSpeechInterface.py (former TextToSpeech.py)
Version 3.1

Library of text to speech functions for Aiko.

Requirements:

- mpg123 and ffmpeg installed and added to PATH

pip install:

- elevenlabslib
- pydub
- gtts
- speech recognition
- pyaudio

Changelog:

- Separated gtts text-to-speech into its own function (generate_mp3_gtts). 
- Added a new function to include elevenlabs text-to-speech functionality (generate_mp3_elevenlabs).
- Major rework to the say() function:
- Now, instead of generating audio, it serves as a controler for Aiko's tts. If the elevenlabs parameter is set to true,
it will generate audio using the elevenlab function. If not, it will generate audio using the gtts function.

"""

import gtts                     # text to mp3 file
import os                       # to play audio file using mpg123
from pydub import AudioSegment  # to increase text-to-speech audio pitch
from elevenlabslib import *     # elevenlabs API python integration
import speech_recognition as sr # speech-to-text


# elevenlabs voicetype. this is a list because multiple voices can have the same name
try:
    # set elevenlabs api key here. only required if you intend to use elevenlabs tts.
    user = ElevenLabsUser(open("key_elevenlabs.txt", "r").read().strip('\n'))
    voice = user.get_voices_by_name("asuka-langley-yuko-miyamura")[0]
except:
    voice = ''

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

def generate_mp3_gtts(text : str, to_pitch_shift = False, pitch_shift = 1.0, tld = 'us', lang = 'en', slow = False):
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

def generate_mp3_elevenlabs(text):
    """Generates a text-to-speech mp3 file using elevenlabs API. Returns the name of the generated audio file.
     """

    audio_file = "audio.mp3"
    mp3_bytes = voice.generate_audio_bytes(prompt = text, stability = 0.75, similarity_boost = 0.75)

    with open(audio_file, "wb") as f:
        f.write(mp3_bytes)

    return(audio_file)

def say(text: str, elevenlabs = False, lang = 'en', audiodevice = "2"):
    """ Will play either gtts or elevenlabs text-to-speech depending on the parameter and language
    (elevenlabs only supports the english language, currently.) If elevenlabs text-to-speech fails to generate, 
    the function will default to playing gtts. """

    if elevenlabs and lang == 'en':
        try:
            audio = generate_mp3_elevenlabs(text)
        except Exception as e:
            audio = generate_mp3_gtts(text, to_pitch_shift = True, pitch_shift = 2.0, tld = "co.uk")
    elif lang == 'en':
        audio = generate_mp3_gtts(text, to_pitch_shift = True, pitch_shift = 2.0, tld = "co.uk")
    else:
        audio = generate_mp3_gtts(text, to_pitch_shift = True, pitch_shift = 2.0, lang = lang)

    os.system(f"mpg123 -q --audiodevice {audiodevice} {audio}")
    os.remove(audio)

def listen(prompt=''):
    """
    Uses SpeechRecognition library to listen to audio input from a microphone and convert any speech it detects to text using 
    Google's speech recognition API. Returns the recognized text as a string or None if no speech is detected. Takes an 
    optional prompt parameter to print a prompt text to the console before listening for audio input.
    """
    r = sr.Recognizer()
    text = None

    if prompt != '':
        print(prompt)

    
    with sr.Microphone() as source:
        audio = r.listen(source)
        text = r.recognize_google(audio)


    return text 

if __name__ == "__main__":
    #userspeech = listen('Listening...')
    #print(userspeech)
    say("Hello Rchart-Kun!", elevenlabs=True)
    #say("Hello Rchart-Kun! 1", audiodevice = 1)
    #say("Hello Rchart-Kun! 2", audiodevice = 2)
    #say("Hello Rchart-Kun! 3", audiodevice = 3)
    #say("Hello Rchart-Kun! 4", audiodevice = 4)