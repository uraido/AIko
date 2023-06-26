'''
AikoINIhandler.py

Version 2.0

Parses Aikos INI configuration file and adds any missing values to avoid raising any missing value exceptions.

Changelog:
20:
- Removed a bunch of old, unused settings and sections.
- Replaced SILENCE_BREAKER section with SPONTANEOUS_TALKING section.
21:
- Fixed typo in azure_voice default value.
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
        'SPONTANEOUS_TALKING',
        'LIVESTREAM',
    ]

    # the options each section should contain, followed by their default values and comments.
    GENERAL = [
        ('username', 'Ulaidh'),
        ('breaker_phrase', 'code red'),
        ('dynamic_scenarios', 'True'),
        ('completion_timeout', '10'),
    ]

    VOICE = [
        ('azure_voice', 'en-US-SaraNeural'),
        ('azure_region', 'brazilsouth'),
        ('audio_device', 'Cable Input'),
        ('mic_device', 'Cable-B Output'),
    ]

    SPONTANEOUS_TALKING = [
        ('min_time', '180'),
        ('max_time', '540'),
    ]

    LIVESTREAM = [
        ('liveid', ''),
        ('toggle_listening', 'Page Down')
    ]

    # saves the lists containing the values in a dictionary, with their respective sections as the key
    options = {
        'GENERAL': GENERAL,
        'VOICE': VOICE,
        'SPONTANEOUS_TALKING': SPONTANEOUS_TALKING,
        'LIVESTREAM': LIVESTREAM,
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
