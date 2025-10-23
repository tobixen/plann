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
import json
import time

from plann.ollama import OllamaClient, NaturalLanguageParser, format_for_plann
from plann.config import read_config, expand_config_section
from plann.lib import find_calendars
from plann.commands import _add_event, _add_todo


class ConfigDialog:
    """Configuration dialog for CalDAV settings"""

    def __init__(self, parent=None):
        self.result = None

        # Create dialog window
        if parent:
            self.dialog = tk.Toplevel(parent)
        else:
            self.dialog = tk.Tk()

        self.dialog.title("Configuration CalDAV")
        self.dialog.geometry("500x450")
        self.dialog.resizable(False, False)

        # Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (450 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self.create_widgets()

        # Make modal
        if parent:
            self.dialog.transient(parent)
            self.dialog.grab_set()

    def create_widgets(self):
        """Create configuration form widgets"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            main_frame,
            text="Configuration CalDAV",
            font=('Arial', 14, 'bold')
        )
        title.pack(pady=(0, 20))

        # Info text
        info = ttk.Label(
            main_frame,
            text="Configurez votre serveur CalDAV pour synchroniser\nvos événements et tâches.",
            justify=tk.CENTER
        )
        info.pack(pady=(0, 20))

        # Form frame
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # CalDAV URL
        ttk.Label(form_frame, text="URL CalDAV *").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(form_frame, width=40)
        self.url_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        self.url_entry.insert(0, "https://")

        ttk.Label(
            form_frame,
            text="Ex: https://nextcloud.com/remote.php/dav/",
            font=('Arial', 8),
            foreground='gray'
        ).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        # Username
        ttk.Label(form_frame, text="Utilisateur *").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.user_entry = ttk.Entry(form_frame, width=40)
        self.user_entry.grid(row=2, column=1, pady=5, padx=(10, 0))

        # Password
        ttk.Label(form_frame, text="Mot de passe *").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.pass_entry = ttk.Entry(form_frame, width=40, show="*")
        self.pass_entry.grid(row=3, column=1, pady=5, padx=(10, 0))

        # Section name
        ttk.Label(form_frame, text="Nom de section").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.section_entry = ttk.Entry(form_frame, width=40)
        self.section_entry.grid(row=4, column=1, pady=5, padx=(10, 0))
        self.section_entry.insert(0, "default")

        ttk.Label(
            form_frame,
            text="Par défaut : 'default'",
            font=('Arial', 8),
            foreground='gray'
        ).grid(row=5, column=1, sticky=tk.W, padx=(10, 0))

        # Test result label
        self.test_result_label = ttk.Label(
            form_frame,
            text="",
            font=('Arial', 9)
        )
        self.test_result_label.grid(row=6, column=0, columnspan=2, pady=10)

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(20, 0))

        # Test button
        self.test_button = ttk.Button(
            button_frame,
            text="Tester la connexion",
            command=self.test_connection
        )
        self.test_button.pack(side=tk.LEFT, padx=5)

        # Save button
        self.save_button = ttk.Button(
            button_frame,
            text="Sauvegarder",
            command=self.save_config
        )
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Cancel button
        ttk.Button(
            button_frame,
            text="Annuler",
            command=self.dialog.destroy
        ).pack(side=tk.LEFT, padx=5)

    def test_connection(self):
        """Test CalDAV connection"""
        url = self.url_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.pass_entry.get()

        if not url or not user or not password:
            self.test_result_label.config(
                text="❌ Tous les champs obligatoires doivent être remplis",
                foreground='red'
            )
            return

        self.test_button.config(state=tk.DISABLED, text="Test en cours...")
        self.test_result_label.config(text="⏳ Test de connexion...", foreground='orange')
        self.dialog.update()

        # Test in background
        threading.Thread(target=self._test_connection_thread, args=(url, user, password), daemon=True).start()

    def _test_connection_thread(self, url, user, password):
        """Test connection in background thread"""
        try:
            import caldav

            # Try to connect
            client = caldav.DAVClient(
                url=url,
                username=user,
                password=password
            )

            principal = client.principal()
            calendars = principal.calendars()

            if calendars:
                self.dialog.after(0, lambda: self.test_result_label.config(
                    text=f"✅ Connexion réussie ! {len(calendars)} calendrier(s) trouvé(s)",
                    foreground='green'
                ))
            else:
                self.dialog.after(0, lambda: self.test_result_label.config(
                    text="⚠️ Connexion OK mais aucun calendrier trouvé",
                    foreground='orange'
                ))

        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 80:
                error_msg = error_msg[:80] + "..."
            self.dialog.after(0, lambda: self.test_result_label.config(
                text=f"❌ Erreur : {error_msg}",
                foreground='red'
            ))

        finally:
            self.dialog.after(0, lambda: self.test_button.config(state=tk.NORMAL, text="Tester la connexion"))

    def save_config(self):
        """Save configuration to file"""
        url = self.url_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.pass_entry.get()
        section = self.section_entry.get().strip() or "default"

        if not url or not user or not password:
            messagebox.showerror(
                "Champs manquants",
                "Veuillez remplir tous les champs obligatoires (*)."
            )
            return

        # Config file path
        config_path = os.path.expanduser("~/.config/calendar.conf")
        config_dir = os.path.dirname(config_path)

        # Create config directory if needed
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
            except Exception as e:
                messagebox.showerror(
                    "Erreur",
                    f"Impossible de créer le répertoire de configuration:\n{e}"
                )
                return

        # Load existing config or create new
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)

                # Backup existing file
                backup_path = f"{config_path}.{int(time.time())}.bak"
                os.rename(config_path, backup_path)
            except Exception as e:
                messagebox.showerror(
                    "Erreur",
                    f"Impossible de lire la configuration existante:\n{e}"
                )
                return

        # Add new section
        config[section] = {
            "caldav_url": url,
            "caldav_user": user,
            "caldav_pass": password
        }

        # Save config
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)

            messagebox.showinfo(
                "Configuration sauvegardée",
                f"Configuration sauvegardée avec succès dans:\n{config_path}\n\n"
                f"Section: {section}"
            )

            self.result = config
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Impossible de sauvegarder la configuration:\n{e}"
            )

    def show(self):
        """Show dialog and wait for result"""
        self.dialog.wait_window()
        return self.result


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
            text="Plann AI",
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
            text="[+] Ajouter",
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
            text="[Mic] Vocal",
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

        # Config button
        config_button = tk.Button(
            bottom_frame,
            text="[Config]",
            command=self.open_config_dialog,
            bg='#6c757d',
            fg='white',
            font=('Arial', 9),
            relief=tk.FLAT,
            padx=10,
            pady=2,
            cursor='hand2'
        )
        config_button.pack(side=tk.RIGHT, padx=(0, 5))

        # Clear history button
        clear_button = tk.Button(
            bottom_frame,
            text="[Effacer]",
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
        help_message = """Plann n'est pas encore configuré !

Voulez-vous ouvrir l'assistant de configuration ?

Cela vous permettra de configurer facilement
votre serveur CalDAV."""

        response = messagebox.askyesno(
            "Configuration requise",
            help_message,
            icon='question'
        )

        if response:  # User wants to configure
            self.open_config_dialog()
        else:
            # Ask if they want to quit
            if messagebox.askyesno(
                "Quitter ?",
                "Voulez-vous quitter l'application ?\n\n"
                "Sans configuration, vous ne pourrez pas ajouter d'événements.",
                icon='warning'
            ):
                self.root.quit()
                sys.exit(0)

    def open_config_dialog(self):
        """Open configuration dialog"""
        dialog = ConfigDialog(self.root)
        result = dialog.show()

        if result:
            # Configuration saved, reload
            self.log_message("✓ Configuration sauvegardée, rechargement...", 'success')
            self.config_loaded = self.load_config()
            self.update_ui_state()

            if self.config_loaded:
                messagebox.showinfo(
                    "Succès",
                    "Configuration chargée avec succès !\n\n"
                    "Vous pouvez maintenant ajouter des événements et tâches."
                )

    def update_status(self):
        """Update Ollama connection status"""
        if not self.config_loaded:
            self.status_label.config(
                text="[X] Configuration requise",
                foreground='#d9534f'
            )
        elif self.ollama_available:
            self.status_label.config(
                text=f"[OK] Connecté à Ollama ({self.model})",
                foreground='#5cb85c'
            )
        else:
            self.status_label.config(
                text="[X] Ollama non disponible",
                foreground='#d9534f'
            )

    def update_ui_state(self):
        """Update UI elements based on configuration status"""
        if not self.config_loaded:
            # Disable action buttons if not configured
            self.add_button.config(state=tk.DISABLED)
            self.voice_button.config(state=tk.DISABLED)
            self.text_input.config(state=tk.DISABLED)
        else:
            # Enable action buttons if configured
            self.add_button.config(state=tk.NORMAL)
            self.voice_button.config(state=tk.NORMAL)
            self.text_input.config(state=tk.NORMAL)

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
        self.add_button.config(state=tk.DISABLED, text="[...] Traitement...")

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
            self.root.after(0, lambda: self.add_button.config(state=tk.NORMAL, text="[+] Ajouter"))

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
        self.voice_button.config(state=tk.DISABLED, text="[Mic] Écoute...")

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
            self.root.after(0, lambda: self.voice_button.config(state=tk.NORMAL, text="[Mic] Vocal"))

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
