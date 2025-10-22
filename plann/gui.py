#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal GUI for plann with Ollama integration
A small, always-on-top window for quick event/task entry
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from datetime import datetime
import sys
import os

from plann.ollama import OllamaClient, NaturalLanguageParser, format_for_plann
from plann.config import read_config, expand_config_section
from plann.lib import find_calendars
from plann.commands import _add_event, _add_todo


class PlannGUI:
    """Minimal GUI for plann"""

    def __init__(self, config_section='default', model='llama2', ollama_host='http://localhost:11434'):
        self.config_section = config_section
        self.model = model
        self.ollama_host = ollama_host
        self.config_loaded = False

        # Initialize Ollama client
        self.ollama = OllamaClient(ollama_host)
        self.parser = NaturalLanguageParser(self.ollama, model)

        # Check Ollama connection
        self.ollama_available = self.ollama.is_available()

        # Create main window
        self.root = tk.Tk()
        self.root.title("Plann AI")

        # Set window size and position
        window_width = 400
        window_height = 500

        # Position in top-right corner
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - window_width - 20
        y = 50

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Always on top
        self.root.attributes('-topmost', True)

        # Style
        self.setup_styles()

        # Create UI
        self.create_widgets()

        # Load config and calendars
        self.config_loaded = self.load_config()

        # Update UI based on configuration status
        self.update_ui_state()

    def setup_styles(self):
        """Setup UI styles"""
        style = ttk.Style()
        style.theme_use('clam')

        # Colors
        bg_color = '#2b2b2b'
        fg_color = '#ffffff'
        entry_bg = '#3c3c3c'
        button_bg = '#4a9eff'
        success_bg = '#5cb85c'
        error_bg = '#d9534f'

        # Configure styles
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Arial', 10))
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 9))
        style.configure('TButton', font=('Arial', 10), padding=5)
        style.configure('Add.TButton', background=button_bg, foreground='white')
        style.configure('Voice.TButton', background=success_bg, foreground='white')

        # Main window background
        self.root.configure(bg=bg_color)

    def create_widgets(self):
        """Create GUI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="📅 Plann AI",
            style='Title.TLabel'
        )
        title_label.pack(pady=(0, 10))

        # Status indicator
        self.status_label = ttk.Label(
            main_frame,
            text="",
            style='Status.TLabel'
        )
        self.status_label.pack()

        # Separator
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)

        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        input_label = ttk.Label(input_frame, text="Décrivez votre événement ou tâche :")
        input_label.pack(anchor='w')

        # Text input
        self.text_input = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            font=('Arial', 10),
            bg='#3c3c3c',
            fg='white',
            insertbackground='white',
            relief=tk.FLAT,
            padx=5,
            pady=5
        )
        self.text_input.pack(fill=tk.X, pady=(5, 0))
        self.text_input.bind('<Return>', self.on_enter_key)
        self.text_input.focus()

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))

        # Add button
        self.add_button = tk.Button(
            buttons_frame,
            text="➕ Ajouter",
            command=self.add_event,
            bg='#4a9eff',
            fg='white',
            font=('Arial', 10, 'bold'),
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor='hand2'
        )
        self.add_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        # Voice button
        self.voice_button = tk.Button(
            buttons_frame,
            text="🎤 Vocal",
            command=self.voice_input,
            bg='#5cb85c',
            fg='white',
            font=('Arial', 10, 'bold'),
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor='hand2'
        )
        self.voice_button.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Separator
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=10)

        # History label
        history_label = ttk.Label(main_frame, text="Historique récent :")
        history_label.pack(anchor='w')

        # History text area
        self.history_text = scrolledtext.ScrolledText(
            main_frame,
            height=12,
            wrap=tk.WORD,
            font=('Courier', 9),
            bg='#3c3c3c',
            fg='#d0d0d0',
            relief=tk.FLAT,
            padx=5,
            pady=5,
            state=tk.DISABLED
        )
        self.history_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Configure tags for colored output
        self.history_text.tag_config('success', foreground='#5cb85c')
        self.history_text.tag_config('error', foreground='#d9534f')
        self.history_text.tag_config('info', foreground='#4a9eff')
        self.history_text.tag_config('time', foreground='#888888')

        # Bottom frame with options
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))

        # Always on top checkbox
        self.always_on_top_var = tk.BooleanVar(value=True)
        always_on_top_cb = tk.Checkbutton(
            bottom_frame,
            text="Toujours au premier plan",
            variable=self.always_on_top_var,
            command=self.toggle_always_on_top,
            bg='#2b2b2b',
            fg='white',
            selectcolor='#3c3c3c',
            activebackground='#2b2b2b',
            activeforeground='white',
            font=('Arial', 9)
        )
        always_on_top_cb.pack(side=tk.LEFT)

        # Clear history button
        clear_button = tk.Button(
            bottom_frame,
            text="🗑️ Effacer",
            command=self.clear_history,
            bg='#6c757d',
            fg='white',
            font=('Arial', 9),
            relief=tk.FLAT,
            padx=10,
            pady=2,
            cursor='hand2'
        )
        clear_button.pack(side=tk.RIGHT)

    def load_config(self):
        """Load plann configuration and calendars"""
        try:
            config_data = read_config()
            self.config = expand_config_section(config_data, self.config_section)

            # Find calendars
            self.calendars = find_calendars(self.config, raise_errors=False)

            if not self.calendars:
                self.log_message("⚠️ Aucun calendrier trouvé. Configurez plann d'abord.", 'error')
                self.show_config_help()
                return False
            else:
                self.log_message(f"✓ {len(self.calendars)} calendrier(s) trouvé(s)", 'success')
                return True

        except Exception as e:
            self.config = None
            self.calendars = []
            self.log_message(f"⚠️ Erreur de configuration: {e}", 'error')
            self.show_config_help()
            return False

    def show_config_help(self):
        """Show configuration help dialog"""
        config_path = os.path.expanduser("~/.config/calendar.conf")

        help_message = f"""Plann n'est pas encore configuré !

Pour utiliser plann-ai-gui, vous devez d'abord configurer plann :

1. Créez le fichier de configuration :
   {config_path}

2. Ajoutez vos paramètres CalDAV (exemple) :

   {{
     "default": {{
       "caldav_url": "https://votre-serveur.com/caldav/",
       "caldav_user": "votre_utilisateur",
       "caldav_pass": "votre_mot_de_passe"
     }}
   }}

3. Testez votre configuration :
   plann list-calendars

Pour plus d'informations, consultez :
   plann --help

Voulez-vous quitter l'application ?"""

        response = messagebox.askyesno(
            "Configuration requise",
            help_message,
            icon='warning'
        )

        if response:  # User clicked "Yes" to quit
            self.root.quit()
            sys.exit(0)

    def update_status(self):
        """Update Ollama connection status"""
        if not self.config_loaded:
            self.status_label.config(
                text="🔴 Configuration requise",
                foreground='#d9534f'
            )
        elif self.ollama_available:
            self.status_label.config(
                text=f"🟢 Connecté à Ollama ({self.model})",
                foreground='#5cb85c'
            )
        else:
            self.status_label.config(
                text="🔴 Ollama non disponible",
                foreground='#d9534f'
            )

    def update_ui_state(self):
        """Update UI elements based on configuration status"""
        if not self.config_loaded:
            # Disable action buttons if not configured
            self.add_button.config(state=tk.DISABLED)
            self.voice_button.config(state=tk.DISABLED)
            self.text_input.config(state=tk.DISABLED)

        # Update status regardless
        self.update_status()

    def toggle_always_on_top(self):
        """Toggle always on top"""
        self.root.attributes('-topmost', self.always_on_top_var.get())

    def on_enter_key(self, event):
        """Handle Enter key in text input"""
        if event.state & 0x1:  # Shift+Enter: new line
            return
        else:  # Enter: add event
            self.add_event()
            return 'break'

    def add_event(self):
        """Add event/task from text input"""
        text = self.text_input.get("1.0", tk.END).strip()

        if not text:
            return

        if not self.ollama_available:
            messagebox.showerror(
                "Ollama non disponible",
                "Ollama n'est pas accessible. Assurez-vous qu'il est en cours d'exécution:\n\n"
                "ollama serve"
            )
            return

        if not self.calendars:
            messagebox.showerror(
                "Aucun calendrier",
                "Aucun calendrier trouvé.\n\n"
                "Configurez plann d'abord avec: plann --help"
            )
            return

        # Disable button during processing
        self.add_button.config(state=tk.DISABLED, text="⏳ Traitement...")

        # Process in background thread
        threading.Thread(target=self._process_event, args=(text,), daemon=True).start()

    def _process_event(self, text):
        """Process event in background thread"""
        try:
            # Log input
            self.log_message(f"📝 Entrée: {text}", 'info')

            # Parse with Ollama
            parsed = self.parser.parse_event(text)

            # Format for plann
            command_name, timespec, summary, kwargs = format_for_plann(parsed)

            # Create a mock context object for plann functions
            class MockContext:
                def __init__(self, calendars):
                    self.obj = {
                        'calendars': calendars,
                        'ical_fragment': ''
                    }

            ctx = MockContext(self.calendars)

            # Execute
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
                event_icon = "✓"

            elif kwargs.get('event'):
                # Prepare kwargs for _add_event
                event_kwargs = {'summary': (summary,)}
                if kwargs.get('alarm'):
                    event_kwargs['alarm'] = kwargs['alarm']

                _add_event(ctx, timespec, **event_kwargs)
                event_icon = "📅"

            # Log success
            self.log_message(f"{event_icon} Ajouté: {summary}", 'success')

            # Clear input
            self.root.after(0, self._clear_input)

        except Exception as e:
            self.log_message(f"❌ Erreur: {str(e)}", 'error')

        finally:
            # Re-enable button
            self.root.after(0, lambda: self.add_button.config(state=tk.NORMAL, text="➕ Ajouter"))

    def _clear_input(self):
        """Clear text input"""
        self.text_input.delete("1.0", tk.END)
        self.text_input.focus()

    def voice_input(self):
        """Voice input mode"""
        try:
            import speech_recognition as sr
        except ImportError:
            messagebox.showerror(
                "Module manquant",
                "Le module 'speech_recognition' n'est pas installé.\n\n"
                "Installez-le avec:\n"
                "pip install SpeechRecognition pyaudio"
            )
            return

        # Disable button
        self.voice_button.config(state=tk.DISABLED, text="🎤 Écoute...")

        # Process in background
        threading.Thread(target=self._voice_input_thread, daemon=True).start()

    def _voice_input_thread(self):
        """Voice input in background thread"""
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()

            with sr.Microphone() as source:
                self.log_message("🎤 Calibration...", 'info')
                recognizer.adjust_for_ambient_noise(source, duration=1)

                self.log_message("🎤 Parlez maintenant...", 'info')
                audio = recognizer.listen(source, timeout=10)

            self.log_message("🎤 Transcription...", 'info')

            try:
                text = recognizer.recognize_google(audio, language='fr-FR')
                self.log_message(f"🎤 Capturé: {text}", 'success')

                # Set text in input
                self.root.after(0, lambda: self.text_input.insert("1.0", text))

                # Auto-add
                self.root.after(500, self.add_event)

            except sr.UnknownValueError:
                self.log_message("❌ Impossible de comprendre l'audio", 'error')
            except sr.RequestError as e:
                self.log_message(f"❌ Erreur du service: {e}", 'error')

        except Exception as e:
            self.log_message(f"❌ Erreur vocale: {str(e)}", 'error')

        finally:
            self.root.after(0, lambda: self.voice_button.config(state=tk.NORMAL, text="🎤 Vocal"))

    def log_message(self, message, tag='info'):
        """Log message to history"""
        def _log():
            self.history_text.config(state=tk.NORMAL)

            # Add timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.history_text.insert(tk.END, f"[{timestamp}] ", 'time')
            self.history_text.insert(tk.END, f"{message}\n", tag)

            # Auto-scroll to bottom
            self.history_text.see(tk.END)

            self.history_text.config(state=tk.DISABLED)

        self.root.after(0, _log)

    def clear_history(self):
        """Clear history text"""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        self.history_text.config(state=tk.DISABLED)

    def run(self):
        """Run the GUI"""
        self.root.mainloop()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Minimal GUI for plann with Ollama")

    parser.add_argument(
        '--model',
        default=os.environ.get('OLLAMA_MODEL', 'llama2'),
        help="Modèle Ollama à utiliser (défaut: llama2)"
    )

    parser.add_argument(
        '--ollama-host',
        default=os.environ.get('OLLAMA_HOST', 'http://localhost:11434'),
        help="URL de l'API Ollama (défaut: http://localhost:11434)"
    )

    parser.add_argument(
        '--config-section',
        default='default',
        help="Section de configuration à utiliser (défaut: default)"
    )

    args = parser.parse_args()

    # Create and run GUI
    app = PlannGUI(
        config_section=args.config_section,
        model=args.model,
        ollama_host=args.ollama_host
    )
    app.run()


if __name__ == '__main__':
    main()
