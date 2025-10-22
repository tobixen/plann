#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plann-ai: Natural language interface for plann using Ollama
"""

import os
import sys
import click
from plann.ollama import OllamaClient, NaturalLanguageParser, format_for_plann, test_ollama_connection
from plann.config import config_section, read_config, expand_config_section
from plann.lib import find_calendars
from plann.commands import _add_event, _add_todo
from plann.metadata import metadata

__version__ = metadata["version"]


@click.command()
@click.argument('text', nargs=-1)
@click.option('--voice', is_flag=True, help="Mode vocal (nécessite speech_recognition)")
@click.option('--model', default=os.environ.get('OLLAMA_MODEL', 'llama2'), help="Modèle Ollama à utiliser")
@click.option('--ollama-host', default=os.environ.get('OLLAMA_HOST', 'http://localhost:11434'), help="URL de l'API Ollama")
@click.option('--test-connection', is_flag=True, help="Tester la connexion à Ollama et quitter")
@click.option('--dry-run', is_flag=True, help="Afficher ce qui serait fait sans l'exécuter")
@click.option('-c', '--config-file', default=f"{os.environ.get('HOME')}/.config/calendar.conf", help="Configuration file")
@click.option('--config-section', default="default", help="Section de configuration")
@click.option('--caldav-url', help="Full URL to the caldav server", metavar='URL')
@click.option('--caldav-username', '--caldav-user', help="Username for the caldav server")
@click.option('--caldav-password', '--caldav-pass', help="Password for the caldav server")
@click.option('--calendar-url', help="Calendar id, path or URL", metavar='cal')
@click.option('--debug', is_flag=True, help="Afficher les informations de débogage")
@click.pass_context
def cli(ctx, text, voice, model, ollama_host, test_connection, dry_run, config_file, config_section,
        caldav_url, caldav_username, caldav_password, calendar_url, debug):
    """
    plann-ai: Add events and tasks using natural language with Ollama

    Examples:
        plann-ai "Rendez-vous dentiste demain à 14h"
        plann-ai "Acheter du pain"
        plann-ai --voice
    """

    # Test connection if requested
    if test_connection:
        ollama = OllamaClient(ollama_host)
        test_ollama_connection()
        sys.exit(0 if ollama.is_available() else 1)

    # Get text input
    if voice:
        text_input = get_voice_input()
        if not text_input:
            click.echo("Erreur: Impossible de capturer la voix", err=True)
            sys.exit(1)
        click.echo(f"Texte capturé: {text_input}")
    elif text:
        text_input = ' '.join(text)
    else:
        click.echo(ctx.get_help())
        sys.exit(1)

    # Initialize Ollama client
    ollama = OllamaClient(ollama_host)

    if not ollama.is_available():
        click.echo(f"Erreur: Ollama n'est pas accessible sur {ollama_host}", err=True)
        click.echo("Démarrez-le avec: ollama serve", err=True)
        sys.exit(1)

    # Check if model is available
    available_models = ollama.list_models()
    if model not in [m.split(':')[0] for m in available_models]:
        click.echo(f"Avertissement: Le modèle '{model}' n'est peut-être pas installé", err=True)
        click.echo(f"Modèles disponibles: {', '.join(available_models)}", err=True)
        click.echo(f"Installez-le avec: ollama pull {model}", err=True)

    # Parse natural language
    click.echo(f"Analyse du texte avec {model}...")
    parser = NaturalLanguageParser(ollama, model)

    try:
        parsed = parser.parse_event(text_input)

        if debug:
            import json
            click.echo("\nDonnées parsées:")
            click.echo(json.dumps(parsed, indent=2, ensure_ascii=False))

        # Convert to plann format
        command_name, timespec, summary, kwargs = format_for_plann(parsed)

        if debug:
            click.echo(f"\nCommande: {command_name}")
            click.echo(f"Timespec: {timespec}")
            click.echo(f"Summary: {summary}")
            click.echo(f"Kwargs: {kwargs}")

        if dry_run:
            event_type = "event" if kwargs.get('event') else "todo"
            click.echo(f"\n[DRY RUN] Ajouterait un {event_type}:")
            click.echo(f"  Résumé: {summary}")
            if timespec:
                click.echo(f"  Date/heure: {timespec}")
            if kwargs.get('set_due'):
                click.echo(f"  Échéance: {kwargs['set_due']}")
            if kwargs.get('set_priority'):
                click.echo(f"  Priorité: {kwargs['set_priority']}")
            click.echo("\n(Mode dry-run: commande non exécutée)")
            sys.exit(0)

        # Setup context like plann does
        ctx.ensure_object(dict)

        # Read configuration
        config_data = read_config(config_file)
        config = expand_config_section(config_data, config_section)

        # Override with command line options
        if caldav_url:
            config['caldav_url'] = caldav_url
        if caldav_username:
            config['caldav_username'] = caldav_username
        if caldav_password:
            config['caldav_password'] = caldav_password
        if calendar_url:
            config['calendar_url'] = [calendar_url]

        # Find calendars
        calendars = find_calendars(config, raise_errors=True)
        ctx.obj['calendars'] = calendars

        if not calendars:
            click.echo("Erreur: Aucun calendrier trouvé", err=True)
            click.echo("Configurez plann avec: plann --interactive-config", err=True)
            sys.exit(1)

        # Use first calendar
        ctx.obj['ical_fragment'] = ""

        # Execute the appropriate command
        if kwargs.get('todo'):
            # Prepare kwargs for _add_todo
            todo_kwargs = {'summary': (summary,)}
            if kwargs.get('set_due'):
                todo_kwargs['set_due'] = kwargs['set_due']
            if kwargs.get('set_priority'):
                todo_kwargs['set_priority'] = kwargs['set_priority']
            if kwargs.get('set_alarm'):
                todo_kwargs['set_alarm'] = kwargs['set_alarm']

            _add_todo(ctx, **todo_kwargs)
            click.echo(f"✓ Tâche ajoutée: {summary}")

        elif kwargs.get('event'):
            # Prepare kwargs for _add_event
            event_kwargs = {'summary': (summary,)}
            if kwargs.get('alarm'):
                event_kwargs['alarm'] = kwargs['alarm']

            _add_event(ctx, timespec, **event_kwargs)
            click.echo(f"✓ Événement ajouté: {summary}")

    except Exception as e:
        click.echo(f"Erreur: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def get_voice_input():
    """
    Capture voice input and convert to text
    Requires speech_recognition module
    """
    try:
        import speech_recognition as sr
    except ImportError:
        click.echo("Erreur: Le module 'speech_recognition' n'est pas installé", err=True)
        click.echo("Installez-le avec: pip install SpeechRecognition", err=True)
        return None

    recognizer = sr.Recognizer()

    click.echo("Parlez maintenant... (appuyez sur Ctrl+C pour annuler)")

    try:
        with sr.Microphone() as source:
            # Adjust for ambient noise
            click.echo("Calibration du microphone...")
            recognizer.adjust_for_ambient_noise(source, duration=1)

            click.echo("Écoute...")
            audio = recognizer.listen(source, timeout=10)

        click.echo("Transcription...")

        # Try Google Speech Recognition
        try:
            text = recognizer.recognize_google(audio, language='fr-FR')
            return text
        except sr.UnknownValueError:
            click.echo("Impossible de comprendre l'audio", err=True)
            return None
        except sr.RequestError as e:
            click.echo(f"Erreur du service de reconnaissance vocale: {e}", err=True)
            return None

    except KeyboardInterrupt:
        click.echo("\nAnnulé par l'utilisateur")
        return None
    except Exception as e:
        click.echo(f"Erreur lors de la capture vocale: {e}", err=True)
        return None


if __name__ == '__main__':
    cli()
