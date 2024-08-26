# Pursuer AI Assistant Chat Program Version 1.0 Public Release 1
# Uses Requests Library
# Created by alby13 - https://www.singularityon.com

import os
import logging
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from tkinter import font as tkfont
import re
from datetime import datetime
import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import webbrowser

# Configure error logging
log_file = "error_log.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class CustomHandler(logging.Handler):
    def emit(self, record):
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"Log file updated at {current_time}.")

logger.addHandler(CustomHandler())

class ChatApp:
    def __init__(self, master):
        self.master = master
        self.master.title("")

        # Enable window resizing
        self.master.resizable(True, True)

        self.dragging = False
        self.start_x = 0
        self.start_y = 0

        self.current_line= ""
        self.in_code_block = False
        self.current_format = set()

        self.link_count = 0  

        # Available models
        self.available_models = ["Meta-Llama-3.1-8B-Instruct", "Mistral-Nemo-12B-Instruct-2407"]

        # Default settings
        self.default_settings = {
            "system_prompt": "You are a helpful AI assistant.",
            "repetition_penalty": 1.0,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_tokens": 1024,
            "max_history_chars": 4000,
            "model": self.available_models[0],
            "window": {
                "width": 800,
                "height": 600,
                "x": 100,
                "y": 100
            }
        }

        # Load settings if file exists
        self.load_settings()

        # Set the initial window geometry from settings or default
        self.set_initial_geometry()

        # Bind the close event to on_close
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

        # Set the model from settings
        self.model = self.settings["model"]

        master.geometry("800x600")
        self.maximized = False
        self.original_geometry = master.geometry()

        self.chat_history_file = "chat_history.txt"
        self.max_history_chars = 8000

        self.font_size = 12
        self.create_widgets()
        self.add_resize_functionality()
        self.load_chat_history()
        self.load_api_key()
        self.model = "Meta-Llama-3.1-8B-Instruct"

        self.dragging = False
        self.start_x = 0
        self.start_y = 0

    def load_api_key(self):
        try:
            with open("api_key.txt", "r") as f:
                self.api_key = f.read().strip()
        except FileNotFoundError:
            self.api_key = ""

    def save_api_key(self):
        with open("api_key.txt", "w") as f:
            f.write(self.api_key)

    def create_widgets(self):
        self.master.configure(bg='#282c34')
        self.master.overrideredirect(True)

        self.font = tkfont.Font(family="Arial", size=self.font_size)

        # Title bar
        self.title_bar = tk.Frame(self.master, bg='#1e2227', relief='raised', bd=2, height=30)
        self.title_bar.pack(expand=0, fill=tk.X)
        self.title_bar.bind('<Button-1>', self.start_move)
        self.title_bar.bind('<ButtonRelease-1>', self.stop_move)
        self.title_bar.bind('<B1-Motion>', self.do_move)

        self.close_button = tk.Button(self.title_bar, text='X', command=self.master.quit, bg='#1e2227', fg='white', bd=0)
        self.close_button.pack(side=tk.RIGHT)

        self.maximize_button = tk.Button(self.title_bar, text='□', command=self.toggle_maximize, bg='#1e2227', fg='white', bd=0)
        self.maximize_button.pack(side=tk.RIGHT)

        self.minimize_button = tk.Button(self.title_bar, text='_', command=self.minimize, bg='#1e2227', fg='white', bd=0)
        self.minimize_button.pack(side=tk.RIGHT)

        self.stay_on_top_button = tk.Button(self.title_bar, text='↑', command=self.toggle_stay_on_top, bg='#1e2227', fg='white', bd=0)
        self.stay_on_top_button.pack(side=tk.RIGHT)

        self.settings_button = tk.Button(self.title_bar, text='⚙', command=self.open_settings, bg='#1e2227', fg='white', bd=0)
        self.settings_button.pack(side=tk.RIGHT)

        # Add a vertical separator
        separator = tk.Frame(self.title_bar, width=1, bg='white')
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        self.clear_screen_button = tk.Button(self.title_bar, text='Clear Screen', command=self.clear_screen, bg='#1e2227', fg='white', bd=0)
        self.clear_screen_button.pack(side=tk.LEFT)

        # Add a vertical separator
        separator = tk.Frame(self.title_bar, width=1, bg='white')
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        self.clear_history_button = tk.Button(self.title_bar, text='Clear History', command=self.clear_history, bg='#1e2227', fg='white', bd=0)
        self.clear_history_button.pack(side=tk.LEFT)

        # Add a vertical separator
        separator = tk.Frame(self.title_bar, width=1, bg='white')
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        # Add font size buttons
        self.font_increase_button = tk.Button(self.title_bar, text='A+', command=lambda: self.increase_font_size(None), bg='#1e2227', fg='white', bd=0)
        self.font_increase_button.pack(side=tk.RIGHT)

        self.font_decrease_button = tk.Button(self.title_bar, text='A-', command=lambda: self.decrease_font_size(None), bg='#1e2227', fg='white', bd=0)
        self.font_decrease_button.pack(side=tk.RIGHT)

        # Help button message
        self.help_button = tk.Button(self.title_bar, text='Help', command=self.show_help, bg='#1e2227', fg='white', bd=0)
        self.help_button.pack(side=tk.RIGHT)

        self.chat_display = scrolledtext.ScrolledText(
            self.master, wrap=tk.WORD, bg="#282c34", fg="#D3D3D3", insertbackground="#D3D3D3", font=self.font
        )
        self.chat_display.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.chat_display.bind("<Key>", lambda event: "break")

        # Create additional fonts
        self.bold_font = tkfont.Font(family="Arial", size=self.font_size, weight="bold")
        self.italic_font = tkfont.Font(family="Arial", size=self.font_size, slant="italic")
        self.code_font = tkfont.Font(family="Courier", size=self.font_size)

        # Configure tags for different styles
        self.chat_display.tag_configure('bold', font=self.bold_font)
        self.chat_display.tag_configure('italic', font=self.italic_font)
        self.chat_display.tag_configure('code', font=self.code_font, background='#3E4451', foreground='#98C379', selectbackground='#4E5A6B', selectforeground='#98C379')
        self.chat_display.tag_configure('link', foreground='#61AFEF', underline=True)
        self.chat_display.tag_configure('h1', font=tkfont.Font(family="Arial", size=self.font_size+6, weight="bold"))
        self.chat_display.tag_configure('h2', font=tkfont.Font(family="Arial", size=self.font_size+4, weight="bold"))
        self.chat_display.tag_configure('h3', font=tkfont.Font(family="Arial", size=self.font_size+2, weight="bold"))
        self.chat_display.tag_configure('h4', font=tkfont.Font(family="Arial", size=self.font_size+1, weight="bold"))
        self.chat_display.tag_configure('strikethrough', overstrike=True)

        # Bind click event for links
        self.chat_display.tag_bind('link', '<Button-1>', self._click_link)

        self.master.bind("+", self.increase_font_size)
        self.master.bind("-", self.decrease_font_size)

        input_frame = ttk.Frame(self.master, style="Dark.TFrame")
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        input_frame.columnconfigure(0, weight=1)
        self.input_field = ttk.Entry(input_frame, style="Dark.TEntry")
        #self.input_field.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.input_field.grid(row=0, column=0, sticky="ew")
        self.input_field.bind("<Return>", self.send_message)
        self.input_field.bind("<Button-3>", self.input_popup_menu)
        self.chat_display.bind("<Button-3>", self.popup_menu)

        send_button = ttk.Button(
            input_frame, text="Send", command=self.send_message, style="Dark.TButton"
        )
        send_button.grid(row=0, column=1, padx=(5, 0))

        style = ttk.Style()
        style.theme_create(
            "Dark",
            parent="alt",
            settings={
                "TFrame": {"configure": {"background": "#282c34"}},
                "TEntry": {
                    "configure": {"fieldbackground": "#000000", "foreground": "#D3D3D3", "insertcolor": "#D3D3D3"}
                },
                "TButton": {
                    "configure": {
                        "background": "#4f5966",
                        "foreground": "#D3D3D3",
                        "relief": "flat",
                    },
                    "map": {
                        "background": [("active", "#616973")],
                        "foreground": [("active", "#D3D3D3")],
                    },
                },
            },
        )
        style.theme_use("Dark")

    def load_settings(self):
        if os.path.exists("settings.txt"):
            with open("settings.txt", "r") as f:
                loaded_settings = json.load(f)
                # Merge loaded settings with default settings
                self.settings = {**self.default_settings, **loaded_settings}
                # Ensure window settings exist
                if "window" not in self.settings:
                    self.settings["window"] = self.default_settings["window"]
        else:
            self.settings = self.default_settings.copy()

        # Ensure the model is valid
        if self.settings["model"] not in self.available_models:
            self.settings["model"] = self.available_models[0]

    def save_settings(self):
        with open("settings.txt", "w") as f:
            json.dump(self.settings, f, indent=4)

    def save_settings_from_window(self):
        # Update settings from the entry fields
        self.settings["system_prompt"] = self.system_prompt_entry.get()
        self.settings["repetition_penalty"] = float(self.repetition_penalty_entry.get())
        self.settings["temperature"] = float(self.temperature_entry.get())
        self.settings["top_p"] = float(self.top_p_entry.get())
        self.settings["top_k"] = int(self.top_k_entry.get())
        self.settings["max_tokens"] = int(self.max_tokens_entry.get())
        self.settings["max_history_chars"] = int(self.max_history_chars_entry.get())
        self.settings["model"] = self.model_var.get()

        # Update the current model
        self.model = self.settings["model"]

        # Save API key
        self.api_key = self.api_key_entry.get()
        self.save_api_key()

        # Save settings to file
        self.save_settings()

        # Show confirmation message
        messagebox.showinfo("Settings Saved", "Your settings have been saved successfully.")

        # Close the settings window
        self.settings_window.destroy()

    def set_initial_geometry(self):
        w = self.settings["window"]
        self.master.after(100, lambda: self.master.geometry(f"{w['width']}x{w['height']}+{w['x']}+{w['y']}"))

    def show_help(self):
        help_window = tk.Toplevel(self.master)
        help_window.title("Help - Pursuer AI Version 1.0")
        help_window.geometry("600x400")
        help_window.resizable(False, False)

        help_text = """
Welcome to Pursuer AI!

Before you start:
1. Sign up for an account at ArliAI.com with your email.
2. Find your API Key by clicking on the blue profile picture in the top menu.
3. Enter your API Key in the Settings menu of this application.

Button Explanations:
• Clear Screen: Clears the current chat screen. Chat history and context are not deleted.
• Clear History: Erases all chat history. The screen will be cleared when this is done.
• Font Size (A+/-): Increases or decreases the font size of the chat display.
• Settings (⚙): Opens the settings menu to configure the AI and enter your API Key.
• Push Away (↔): Moves other windows away so the AI Assistant can stay in view.
• Stay on Top (↑/↓): Toggles whether the window stays on top of others.
• Minimize (_): Minimizes the window.
• Maximize (□): Toggles between maximized and normal window size.
• Close (X): Closes the application.

Additional Features:
• Resize the window by dragging its edges.
• Use + and - keys to increase or decrease font size.
• Right-click on the chat display or input field for copy/paste options.

Enjoy using Pursuer AI!

This program was created by alby13
https://www.singularityon.com/

        """

        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, width=70, height=20)
        text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

        ok_button = ttk.Button(help_window, text="OK", command=help_window.destroy)
        ok_button.pack(pady=10)

        help_window.transient(self.master)
        help_window.grab_set()
        self.master.wait_window(help_window)

    def update_user_message(self, message):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"You: {message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def clear_screen(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def clear_history(self):
        with open(self.chat_history_file, "w") as f:
            f.write("")
        self.clear_screen()

    def start_move(self, event):
        self.dragging = True
        self.start_x = event.x_root - self.master.winfo_x()
        self.start_y = event.y_root - self.master.winfo_y()

    def stop_move(self, event):
        self.dragging = False

    def do_move(self, event):
        if self.dragging:
            dx = event.x_root - self.start_x
            dy = event.y_root - self.start_y
            x = self.master.winfo_x() + dx
            y = self.master.winfo_y() + dy
            self.master.geometry(f"+{x}+{y}")
            self.start_x = event.x_root
            self.start_y = event.y_root
        self.save_window_position()  # Save position after moving

    def add_resize_functionality(self):
        self.master.bind("<Button-1>", self.start_resize)
        self.master.bind("<ButtonRelease-1>", self.stop_resize)
        self.master.bind("<B1-Motion>", self.do_resize)

    def start_resize(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.start_width = self.master.winfo_width()
        self.start_height = self.master.winfo_height()
        self.resizing = self.get_resize_edge(event)

    def stop_resize(self, event):
        if not self.dragging:
            self.resizing = ""

    def get_resize_edge(self, event):
        edge = ""
        if event.widget == self.master:
            if event.x < 10:
                edge += "W"
            elif event.x > self.master.winfo_width() - 10:
                edge += "E"
            if event.y < 10:
                edge += "N"
            elif event.y > self.master.winfo_height() - 10:
                edge += "S"
        return edge

    def do_resize(self, event):
        if self.resizing:
            dx = event.x_root - self.start_x
            dy = event.y_root - self.start_y
            new_w, new_h = self.start_width, self.start_height
            new_x, new_y = self.master.winfo_x(), self.master.winfo_y()

            if "E" in self.resizing:
                new_w += dx
            if "S" in self.resizing:
                new_h += dy
            if "W" in self.resizing:
                new_w -= dx
                new_x += dx
            if "N" in self.resizing:
                new_h -= dy
                new_y += dy

            # Ensure minimum window size
            new_w = max(new_w, 200)
            new_h = max(new_h, 200)

            self.master.geometry(f"{new_w}x{new_h}+{new_x}+{new_y}")
            self.save_window_position()  # Save position after resizing

    def toggle_maximize(self):
        if self.maximized:
            self.master.geometry(self.original_geometry)
            self.maximized = False
        else:
            self.original_geometry = self.master.geometry()
            screen_width = self.master.winfo_screenwidth()
            screen_height = self.master.winfo_screenheight()
            self.master.geometry(f"{screen_width}x{screen_height}+0+0")
            self.maximized = True
        self.save_window_position()  # Save position after maximizing/restoring

    def minimize(self):
        self.master.overrideredirect(False)
        self.master.iconify()

    def on_close(self):
        self.save_window_position()
        self.save_settings()
        self.master.destroy()

    def save_window_position(self):
        self.settings["window"] = {
            "width": self.master.winfo_width(),
            "height": self.master.winfo_height(),
            "x": self.master.winfo_x(),
            "y": self.master.winfo_y()
        }
        self.save_settings()

    def toggle_stay_on_top(self):
        if self.master.attributes('-topmost'):
            self.master.attributes('-topmost', False)
            self.stay_on_top_button.config(text='↑')
        else:
            self.master.attributes('-topmost', True)
            self.stay_on_top_button.config(text='↓')

    def open_settings(self):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        self.settings_window = tk.Toplevel(self.master)
        self.settings_window.title("Settings")

        # Create a main frame to hold all the widgets
        main_frame = tk.Frame(self.settings_window, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # API Key
        api_key_frame = tk.Frame(main_frame)
        api_key_frame.pack(fill=tk.X, pady=5)
        tk.Label(api_key_frame, text="API Key:").pack(side=tk.LEFT)
        self.api_key_entry = tk.Entry(api_key_frame, width=50, show="*")
        self.api_key_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        self.api_key_entry.insert(0, self.api_key)

        # Model Selection
        model_frame = tk.Frame(main_frame)
        model_frame.pack(fill=tk.X, pady=5)
        tk.Label(model_frame, text="Model:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=self.settings["model"])
        model_menu = tk.OptionMenu(model_frame, self.model_var, *self.available_models)
        model_menu.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # System Prompt
        system_prompt_frame = tk.Frame(main_frame)
        system_prompt_frame.pack(fill=tk.X, pady=5)
        tk.Label(system_prompt_frame, text="System Prompt:").pack(side=tk.LEFT)
        self.system_prompt_entry = tk.Entry(system_prompt_frame, width=50)
        self.system_prompt_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        self.system_prompt_entry.insert(0, self.settings["system_prompt"])

        # Repetition Penalty
        repetition_penalty_frame = tk.Frame(main_frame)
        repetition_penalty_frame.pack(fill=tk.X, pady=5)
        tk.Label(repetition_penalty_frame, text="Repetition Penalty:").pack(side=tk.LEFT)
        self.repetition_penalty_entry = tk.Entry(repetition_penalty_frame, width=50)
        self.repetition_penalty_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        self.repetition_penalty_entry.insert(0, str(self.settings["repetition_penalty"]))

        # Temperature
        temperature_frame = tk.Frame(main_frame)
        temperature_frame.pack(fill=tk.X, pady=5)
        tk.Label(temperature_frame, text="Temperature:").pack(side=tk.LEFT)
        self.temperature_entry = tk.Entry(temperature_frame, width=50)
        self.temperature_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        self.temperature_entry.insert(0, str(self.settings["temperature"]))

        # Top P
        top_p_frame = tk.Frame(main_frame)
        top_p_frame.pack(fill=tk.X, pady=5)
        tk.Label(top_p_frame, text="Top P:").pack(side=tk.LEFT)
        self.top_p_entry = tk.Entry(top_p_frame, width=50)
        self.top_p_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        self.top_p_entry.insert(0, str(self.settings["top_p"]))

        # Top K
        top_k_frame = tk.Frame(main_frame)
        top_k_frame.pack(fill=tk.X, pady=5)
        tk.Label(top_k_frame, text="Top K:").pack(side=tk.LEFT)
        self.top_k_entry = tk.Entry(top_k_frame, width=50)
        self.top_k_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        self.top_k_entry.insert(0, str(self.settings["top_k"]))

        # Max Tokens
        max_tokens_frame = tk.Frame(main_frame)
        max_tokens_frame.pack(fill=tk.X, pady=5)
        tk.Label(max_tokens_frame, text="Max Tokens:").pack(side=tk.LEFT)
        self.max_tokens_entry = tk.Entry(max_tokens_frame, width=50)
        self.max_tokens_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        self.max_tokens_entry.insert(0, str(self.settings["max_tokens"]))

        # Max History Chars
        max_history_chars_frame = tk.Frame(main_frame)
        max_history_chars_frame.pack(fill=tk.X, pady=5)
        tk.Label(max_history_chars_frame, text="Max History Chars:").pack(side=tk.LEFT)
        self.max_history_chars_entry = tk.Entry(max_history_chars_frame, width=50)
        self.max_history_chars_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        self.max_history_chars_entry.insert(0, str(self.settings["max_history_chars"]))

        save_button = tk.Button(self.settings_window, text="Save", command=self.save_settings_from_window)
        save_button.pack(pady=10)

    def increase_font_size(self, event):
        self.font_size += 1
        self.update_font()

    def decrease_font_size(self, event):
        self.font_size -= 1
        self.update_font()

    def update_font(self):
        self.font.configure(size=self.font_size)
        self.chat_display.configure(font=self.font)
        self.chat_display.update()

    def input_popup_menu(self, event):
        try:
            self.input_field.focus_set()
            popup = tk.Menu(self.master, tearoff=0)
            popup.add_command(label="Copy", command=self.copy_input_field)
            popup.add_command(label="Paste", command=self.paste_input_field)
            popup.tk_popup(event.x_root, event.y_root, 0)
        except Exception as e:
            logging.error(f"Error in input popup menu: {str(e)}")

    def copy_input_field(self):
        try:
            selected_text = self.input_field.selection_get()
            self.master.clipboard_clear()
            self.master.clipboard_append(selected_text)
            self.input_field.selection_clear()
        except tk.TclError:
            self.master.clipboard_clear()
            self.master.clipboard_append(self.input_field.get())

    def paste_input_field(self):
        try:
            self.input_field.insert(tk.END, self.master.clipboard_get())
        except tk.TclError:
            pass

    def popup_menu(self, event):
        try:
            self.chat_display.focus_set()
            popup = tk.Menu(self.master, tearoff=0)
            popup.add_command(label="Copy", command=self.copy_chat_display)
            popup.tk_popup(event.x_root, event.y_root, 0)
        except Exception as e:
            logging.error(f"Could not open menu: {str(e)}")
        finally:
            popup.grab_release()

    def copy_chat_display(self):
        try:
            selected_text = self.chat_display.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.master.clipboard_clear()
            self.master.clipboard_append(selected_text)
        except tk.TclError:
            pass  # No selection

    def load_chat_history(self):
        try:
            with open(self.chat_history_file, "r", encoding="utf-8") as f:
                history = f.read()
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.insert(tk.END, history)
                self.chat_display.config(state=tk.DISABLED)
        except UnicodeDecodeError:
            # If UTF-8 fails, try with 'iso-8859-1' encoding
            try:
                with open(self.chat_history_file, "r", encoding="iso-8859-1") as f:
                    history = f.read()
                    self.chat_display.config(state=tk.NORMAL)
                    self.chat_display.insert(tk.END, history)
                    self.chat_display.config(state=tk.DISABLED)
            except Exception as e:
                error_message = f"Encounterd an issue loading chat history: {str(e)}"
                self.update_chat_display(error_message)
                logging.error(error_message)
        except FileNotFoundError:
            pass
        except Exception as e:
            error_message = f"Encounterd an issue loading chat history: {str(e)}"
            self.update_chat_display(error_message)
            logging.error(error_message)

    def save_chat_history(self):
        try:
            with open(self.chat_history_file, "w", encoding="utf-8") as f:
                f.write(self.chat_display.get("1.0", tk.END))
        except Exception as e:
            error_message = f"Error saving chat history: {str(e)}"
            self.update_chat_display(error_message)
            logging.error(error_message)

    def signal_handler(sig, frame):
        print('\nYou pressed Ctrl+C!')
        sys.exit(0)            

    def send_message(self, event=None):
        user_message = self.input_field.get()
        if not user_message:
            return
        
        # Update chat display with user message
        self.update_user_message(user_message)

        self.input_field.delete(0, tk.END)

        # Replace the text area with the "Please Wait..." message
        self.input_field.insert(0, "Please Wait...")
        self.input_field.config(state=tk.DISABLED)

        # Get the chat history
        chat_history = self.chat_display.get("1.0", "end-1c") # Get all text except the last newline

        # Format the chat history
        formatted_history = []
        current_speaker = None
        current_message = ""

        for line in chat_history.split("\n"):
            if line.startswith("You: "):
                if current_speaker and current_message:
                    formatted_history.append({"role": current_speaker, "content": current_message.strip()})
                current_speaker = "user"
                current_message = line[5:]
            elif current_speaker == "user" and line.strip() and not line.startswith("You: "):
                # This is a continuation of the user's message
                current_message += " " + line.strip()
            elif current_speaker == "assistant" or (current_speaker is None and line.strip()):
                # This is either a continuation of the AI's message or the start of a new AI message
                if current_speaker and current_message:
                    formatted_history.append({"role": current_speaker, "content": current_message.strip()})
                current_speaker = "assistant"
                current_message = line.strip()
            elif line.strip() == "":
                if current_speaker and current_message:
                    formatted_history.append({"role": current_speaker, "content": current_message.strip()})
                    current_speaker = None
                    current_message = ""

        # Add the last message if there's any
        if current_speaker and current_message:
            formatted_history.append({"role": current_speaker, "content": current_message.strip()})

        # Remove the last user message from the history if it's the same as the current message
        if formatted_history and formatted_history[-1]["role"] == "user" and formatted_history[-1]["content"] == user_message:
            formatted_history.pop()

        # Truncate the chat history to the last max_history_chars characters
        while len(str(formatted_history)) > self.settings["max_history_chars"]:
            formatted_history.pop(0)

        # Prepare the messages for the API request
        messages = [
            {"role": "system", "content": self.settings["system_prompt"]},
            *formatted_history,
            {"role": "user", "content": user_message}
        ]

        threading.Thread(target=self.make_api_request, args=(messages,)).start()

    def update_chat_display(self, text):
        #self.master.after(0, self._update_chat_display, text)
        self.master.after(0, self._update_chat_display, text)

    def _update_chat_display(self, text):
        self.chat_display.config(state=tk.NORMAL)

        if not self.current_line:
            self.in_code_block = False
            self.current_format.clear()
        
        # Process the incoming text
        self.current_line += text
        lines = self.current_line.split('\n')
        
        # Process all complete lines
        for line in lines[:-1]:
            self._process_line(line)
        
        # Keep the last incomplete line
        self.current_line = lines[-1]

        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def _process_line(self, line):
        #Reset formatting at the start of each line
        current_tags = tuple(self.current_format)
        
        # Check for code block start/end
        if line.strip().startswith('```'):
            if self.in_code_block:
                # End of code block
                self.in_code_block = False
                self.chat_display.insert(tk.END, '\n')
            else:
                # Start of code block
                self.in_code_block = True
                self.code_language = line.strip()[3:].strip()  # Get language specifier if any
            return

        if self.in_code_block:
            self.chat_display.insert(tk.END, line + '\n', 'code')
            return

        # Headers
        if line.startswith('# '):
            self.chat_display.insert(tk.END, line[2:] + '\n', 'h1')
            return
        elif line.startswith('## '):
            self.chat_display.insert(tk.END, line[3:] + '\n', 'h2')
            return
        elif line.startswith('### '):
            self.chat_display.insert(tk.END, line[4:] + '\n', 'h3')
            return
        elif line.startswith('#### '):
            self.chat_display.insert(tk.END, line[5:] + '\n', 'h4')
            return
        elif line.startswith('##### '):
            self.chat_display.insert(tk.END, line[6:] + '\n', 'h5')
            return
        elif line.startswith('###### '):
            self.chat_display.insert(tk.END, line[7:] + '\n', 'h6')
            return

        elif line.strip().startswith('* ') or line.strip().startswith('- '):
            # Bullet points with possible nested formatting
            bullet = "  • "
            content = line.strip()[2:]
            self.chat_display.insert(tk.END, bullet)
        
            # Check if the content is a header example
            header_match = re.match(r'(H[1-6]): (#{1,6} .+)', content)
            if header_match:
                header_type, header_content = header_match.groups()
                self.chat_display.insert(tk.END, f"{header_type}: ")
                self._process_line(header_content)  # Process the header content
            else:
                self._process_inline_formatting(content)
        
            self.chat_display.insert(tk.END, '\n')
        elif re.match(r'^\d+\.\s', line.strip()):
            # Numbered list with possible nested formatting
            match = re.match(r'^(\d+\.\s)(.*)$', line.strip())
            if match:
                number, content = match.groups()
                self.chat_display.insert(tk.END, number)
            
            # Check if the content is a header example
            header_match = re.match(r'(H[1-6]): (#{1,6} .+)', content)
            if header_match:
                header_type, header_content = header_match.groups()
                self.chat_display.insert(tk.END, f"{header_type}: ")
                self._process_line(header_content)  # Process the header content
            else:
                self._process_inline_formatting(content)
            
            self.chat_display.insert(tk.END, '\n')
        else:
            # Regular line with inline formatting
            self._process_inline_formatting(line)
            self.chat_display.insert(tk.END, '\n')

    def _process_inline_formatting(self, text):
        parts = re.split(r'(\[.*?\]\(.*?\)|`.*?`|\*\*.*?\*\*|\*.*?\*|~~.*?~~|!\[.*?\]\(.*?\))', text)
        for part in parts:
            if part.startswith('[') and '](' in part and part.endswith(')'):
                text, url = part[1:-1].split('](')
                tag_name = f'link-{self.link_count}'
                self.chat_display.insert(tk.END, text, ('link', tag_name))
                self.chat_display.tag_bind(tag_name, '<Button-1>', lambda e, url=url: self._click_link(url))
                self.link_count += 1
            elif part.startswith('`') and part.endswith('`'):
                self.chat_display.insert(tk.END, part[1:-1], 'code')
            elif part.startswith('**') and part.endswith('**'):
                self.chat_display.insert(tk.END, part[2:-2], 'bold')
            elif part.startswith('*') and part.endswith('*'):
                self.chat_display.insert(tk.END, part[1:-1], 'italic')
            elif part.startswith('~~') and part.endswith('~~'):
                self.chat_display.insert(tk.END, part[2:-2], 'strikethrough')
            elif part.startswith('![') and '](' in part and part.endswith(')'):
                alt_text, url = part[2:-1].split('](')
                self.chat_display.insert(tk.END, f"[Image: {alt_text}]")
            else:
                self.chat_display.insert(tk.END, part)

    def _click_link(self, url):
        webbrowser.open(url)

    def create_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def make_api_request(self, messages):
        try:
            url = "https://api.arliai.com/v1/chat/completions"

            payload = json.dumps({
                "model": self.settings["model"],
                "messages": messages,
                "repetition_penalty": self.settings["repetition_penalty"],
                "temperature": self.settings["temperature"],
                "top_p": self.settings["top_p"],
                "top_k": self.settings["top_k"],
                "max_tokens": self.settings["max_tokens"],
                "stream": True
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {self.api_key}"
            }

            response = requests.request("POST", url, headers=headers, data=payload, stream=True, timeout=(15, 35))

            if response.status_code == 200:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        #logging.info(f"Received line: {decoded_line}")
                        if decoded_line.startswith("data: "):
                            if decoded_line.strip() == "data: [DONE]":
                                # Stream finished, do any cleanup if needed
                                self.save_chat_history()
                                #self.wait_label.place_forget()
                                self.input_field.config(state=tk.NORMAL)
                                self.input_field.delete(0, tk.END)
                                self.update_chat_display("\n\n\n")  # Add a newline after the full response
                                break
                            try:
                                json_data = json.loads(decoded_line[6:])
                                if 'choices' in json_data and json_data['choices']:
                                    delta = json_data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        full_response += content
                                        #self.master.after(0, self._update_chat_display, content)
                                        self.update_chat_display(content)
                            except json.JSONDecodeError as json_error:
                                logging.error(f"JSON decode error: {str(json_error)}")
                                logging.error(f"Problematic line: {decoded_line}")
                                print("An issue has occured and has been logged in error_log.txt")
                                continue
                        else:
                            self.update_chat_display(f"Unexpected error, line format: {decoded_line}\n")
            else:
                error_message = f"API request failed with status code {response.status_code}"
                #self.master.after(0, self._update_chat_display, error_message)
                self.update_chat_display(error_message, is_user=False)
                logging.error(f"API request failed: {error_message}")
                logging.error(f"Response content: {response.text}")
                self.wait_label.place_forget()

        except requests.exceptions.RequestException as e:
            error_message = f"Please check your Internet Connection, or ArliAI.com service may be temporarily down. \n Network error: {str(e)}"
            self.update_chat_display(error_message, is_user=False)
            logging.error(f"Network error in API call: {str(e)}")
            print("A network issue has occured and has been logged in error_log.txt")
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            self.update_chat_display(error_message, is_user=False)
            logging.error(f"Unexpected error in API call: {str(e)}")
            print("An issue with the server has occured and has been logged in error_log.txt")

if __name__ == "__main__":
    print("Pursuer AI is Starting. Version 1.0. Created by alby13 - https://singularityon.com")
    print("")
    root = tk.Tk()
    print("Launching Assistant Window...")
    print("")
    app = ChatApp(root)
    print("Pursuer AI is now ready. The window should be open and visible.")
    print("If are having problems with the window or program, you should clear")
    print("or delete the text files in the same directory as this program.")
    print("")
    root.mainloop()
    print("Pursuer AI will now exit.")
    print("")
