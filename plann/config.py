import json
import logging
import os
import time
from getpass import getpass

## The config handling logic originated in plann and has been adopted by the
## caldav library - use the caldav implementation rather than carrying a copy.
## (The redundant aliases mark config_section and expand_config_section as
## intentional re-exports, they are used by cli.py)
from caldav.config import config_section as config_section
from caldav.config import expand_config_section as expand_config_section
from caldav.config import read_config as _read_config


def interactive_config(args, config, remaining_argv):

    section = 'default'
    backup = {}
    modified = False

    print("Welcome to the interactive calendar configuration mode")
    print("Warning - untested code ahead, raise issues at config-issues@plann.no or the github issue tracker")
    print("It might be a good idea to read the documentation in parallel if running this for your first time")
    if not config or not hasattr(config, 'keys'):
        config = {}
        print("No valid existing configuration found")
    if config:
        print("The following sections have been found: ")
        print("\n".join(config.keys()))
        if args.config_section and args.config_section != 'default':
            section = args.config_section
        else:
            ## TODO: tab completion
            section = input("Chose one of those, or a new name / no name for a new configuration section: ")
        if section in config:
            backup = config[section].copy()
        print("Using section " + section)
    else:
        section = 'default'

    if section not in config:
        config[section] = {}

    for config_key in ('caldav_url', 'calendar_url', 'caldav_user', 'caldav_pass', 'caldav_proxy', 'ssl_verify_cert', 'language', 'timezone', 'inherits'):

        if config_key == 'caldav_pass':
            print("Config option caldav_pass - old value: **HIDDEN**")
            value = getpass(prompt="Enter new value (or just enter to keep the old): ")
        else:
            print("Config option {} - old value: {}".format(config_key, config[section].get(config_key, '(None)')))
            value = input("Enter new value (or just enter to keep the old): ")

        if value:
            config[section][config_key] = value
            modified = True

    if not modified:
        print("No configuration changes have been done")
    else:
        state = 'start'
        while state == 'start':
            options = []
            if section:
                options.append(('save', f'save configuration into section {section}'))
            if backup or not section:
                options.append(('save_other', 'add this new configuration into a new section in the configuration file'))
            if remaining_argv:
                options.append(('use', 'use this configuration without saving'))
            options.append(('abort', 'abort without saving'))
            print("CONFIGURATION DONE ...")
            for o in options:
                print("Type {} if you want to {}".format(*o))
            cmd = input("Enter a command: ")
            if cmd in ('use', 'abort'):
                state = 'done'
            if cmd in ('save', 'save_other'):
                if cmd == 'save_other':
                    new_section = input("New config section name: ")
                    config[new_section] = config[section]
                    if backup:
                        config[section] = backup
                    else:
                        del config[section]
                    section = new_section
                try:
                    if os.path.isfile(args.config_file):
                        os.rename(args.config_file, f"{args.config_file}.{int(time.time())}.bak")
                    with open(args.config_file, 'w') as outfile:
                        json.dump(config, outfile, indent=4)
                except Exception as e:
                    print(e)
                else:
                    print("Saved config")
                    state = 'done'

    if args.config_section == 'default' and section != 'default':
        config['default'] = config[section]
    return config

def read_config(fn, interactive_error=False):
    """
    Thin wrapper around the caldav library's read_config.  The caldav
    version raises ValueError on a broken config file - plann should
    rather log the problem and carry on.
    """
    try:
        return _read_config(fn) or {}
    except ValueError:
        if interactive_error:
            logging.error("error in config file.  Be aware that the interactive configuration will ignore and overwrite the current broken config file", exc_info=True)
        else:
            logging.error("error in config file.  It will be ignored", exc_info=True)
    return {}
