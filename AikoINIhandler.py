'''
AikoINIhandler.py

Version 0.1

Parses Aikos INI configuration file and adds any missing values to avoid raising any missing value exceptions.
'''

from configparser import ConfigParser
import os

def handle_ini(ini : str = 'AikoPrefs.ini'):

    print(f'AikoINIhandler.py: Parsing {ini}...')
    print()

    # sections the ini file should contain
    sections = [
        'GENERAL',
        'SPEECH_INTERFACE',
        'SUMMARIZATION',
        'SILENCE_BREAKER',
        'LIVESTREAM'
    ]

    # the options each section should contain, followed by their default values and comments.
    GENERAL = [
        ('username', 'Ulaidh'),
        ('breaker_phrase', 'code red'),
        ('context_slots', '5'),
        ('dynamic_scenarios', 'True')
    ]

    SPEECH_INTERFACE = [
        ('audio_device', '2'),
        ('tts_method', 'gtts'),
        ('elevenlabs_voice', 'asuka-langley-yuko-miyamura'),
        ('azure_voice', 'en-US-Sara-Neural'),
        ('azure_region', 'brazilsouth'),
        ('pitch_shift', '2.0')
    ]

    SUMMARIZATION = [
        ('summary_instruction', 'Summarize this shortly without removing core info:'),
        ('context_character_limit', '375')
    ]

    SILENCE_BREAKER = [
        ('min_silence_breaker_time', '9'),
        ('max_silence_breaker_time', '90')
    ]

    LIVESTREAM = [
        ('liveid', ''),
        ('talking_chance', '1'),
        ('ptt_hotkey', 'num minus'),
        ('sp_hotkey', 'num plus')
    ]

    # saves the lists containing the values in a dictionary, with their respective sections as the key
    options = {
        'GENERAL': GENERAL,
        'SPEECH_INTERFACE': SPEECH_INTERFACE,
        'SUMMARIZATION': SUMMARIZATION,
        'SILENCE_BREAKER': SILENCE_BREAKER,
        'LIVESTREAM': LIVESTREAM
    }

    # creates config instance
    config = ConfigParser(allow_no_value=True)

    if os.path.isfile(ini):
        # check if all sections and options are present, and if not, adds them to the file
        config.read(ini)
        for section in sections:
            if section in config:
                for key in options[section]:
                    if config.has_option(section, key[0]):
                        pass
                    else:
                        config.set(section, key[0], key[1])

            else:
                config.add_section(section)
                for key in options[section]:
                    config.set(section, key[0], key[1])

    else:
        # create config file with all keys and sections...
        for section in sections:
            config.add_section(section)
            for key in options[section]:
                config.set(section, key[0], key[1])

    with open(ini, 'w') as configfile:
        config.write(configfile)
