'''
AikoINIhandler.py

Version 1.2

Parses Aikos INI configuration file and adds any missing values to avoid raising any missing value exceptions.

Changelog:
10:
- Added cfg_hotkey to LIVESTREAM section.
11:
- Added LOGGING section with include_context bool option.
12:
- Renamed SPEECH_INTERFACE section to VOICE and removed deprecated settings related to the phased out
AikoSpeechInterface script.
13:
- Replaced ptt_hotkey with toggle_listening.
'''

from configparser import ConfigParser
import os

def handle_ini(ini : str = 'AikoPrefs.ini'):

    print(f'AikoINIhandler.py: Parsing {ini}...')
    print()

    # sections the ini file should contain
    sections = [
        'GENERAL',
        'VOICE',
        'SUMMARIZATION',
        'SILENCE_BREAKER',
        'LIVESTREAM',
        'LOGGING'
    ]

    # the options each section should contain, followed by their default values and comments.
    GENERAL = [
        ('username', 'Ulaidh'),
        ('breaker_phrase', 'code red'),
        ('context_slots', '5'),
        ('dynamic_scenarios', 'True'),
        ('completion_timeout', '10'),
    ]

    VOICE = [
        ('azure_voice', 'en-US-Sara-Neural'),
        ('azure_region', 'brazilsouth'),
        ('audio_device', 'Cable Input'),
    ]

    SUMMARIZATION = [
        ('summary_instruction', 'Summarize this shortly without removing core info:'),
        ('context_character_limit', '375'),
    ]

    SILENCE_BREAKER = [
        ('min_silence_breaker_time', '9'),
        ('max_silence_breaker_time', '90'),
    ]

    LIVESTREAM = [
        ('liveid', ''),
        ('talking_chance', '1'),
        ('toggle_listening', 'Page Down'),
        ('sp_hotkey', 'num plus'),
        ('cfg_hotkey', 'F5'),
    ]

    LOGGING = [
        ('include_context', 'False'),
    ]

    # saves the lists containing the values in a dictionary, with their respective sections as the key
    options = {
        'GENERAL': GENERAL,
        'VOICE': VOICE,
        'SUMMARIZATION': SUMMARIZATION,
        'SILENCE_BREAKER': SILENCE_BREAKER,
        'LIVESTREAM': LIVESTREAM,
        'LOGGING': LOGGING,
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
