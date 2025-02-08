import json
from pathlib import Path
from tkinter import ttk, messagebox, Toplevel, Event
import keyboard
from threading import Thread
from queue import Queue
from keyboard import start_recording, stop_recording

DEFAULT_KEYBINDS = {
    'record': 'ctrl+r',
    'analyze_audio': 'ctrl+a',
    'analyze_screenshot': 'ctrl+shift+a',
    'screenshot': 'ctrl+q'
}

class KeybindManager:
    def __init__(self, config_path='keybinds.config'):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(exist_ok=True, parents=True)
        self.keybinds = self._load_keybinds()
        self.hotkey_handles = {}
        self.callbacks = []
        if not self.config_path.exists():
            self.save_keybinds(DEFAULT_KEYBINDS)
        else:  # Add explicit registration of initial hotkeys
            self._register_hotkeys()
    
    def add_callback(self, callback):
        self.callbacks.append(callback)
    
    def _register_hotkeys(self):
        # Clear existing hotkeys
        for handle in self.hotkey_handles.values():
            keyboard.remove_hotkey(handle)

        # Register new hotkeys
        self.hotkey_handles = {
            'record': keyboard.add_hotkey(self.keybinds['record'], lambda: self._trigger('record')),
            'analyze_audio': keyboard.add_hotkey(self.keybinds['analyze_audio'], lambda: self._trigger('analyze_audio')),
            'analyze_screenshot': keyboard.add_hotkey(self.keybinds['analyze_screenshot'], lambda: self._trigger('analyze_screenshot')),
            'screenshot': keyboard.add_hotkey(self.keybinds['screenshot'], lambda: self._trigger('screenshot'))
        }
    
    def _trigger(self, action):
        for callback in self.callbacks:
            callback(action)

    def _load_keybinds(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    return {
                        k: keyboard.normalize_name(v)
                        for k, v in loaded.items()
                    }
            return DEFAULT_KEYBINDS.copy()
        except Exception:
            return DEFAULT_KEYBINDS.copy()


    def save_keybinds(self, keybinds):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Normalize before saving
            normalized = {
                k: keyboard.normalize_name(v)
                for k, v in keybinds.items()
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(normalized, f, indent=2)
            
            # IMPORTANT: Update in-memory AND trigger refresh
            self.keybinds = normalized.copy()
            self._register_hotkeys()
            
            return True
        except Exception as e:
            print(f"Error saving keybinds: {e}")
            return False


class KeybindDialog(Toplevel):
    def __init__(self, parent, keybind_manager):
        super().__init__(parent)
        self.configure(bg="#2d2d2d")
        self.title("Keybind Settings")
        self.keybind_manager = keybind_manager
        self._create_widgets()
        self._load_current()

    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(padx=10, pady=10)

        self.entries = {}
        for i, (action, label) in enumerate({
            'record': 'Record Key:',
            'analyze_audio': 'Analyze Audio:', 
            'analyze_screenshot': 'Analyze Screenshot:',
            'screenshot': 'Take Screenshot:'
        }.items()):
            ttk.Label(main_frame, text=label).grid(row=i, column=0, sticky='w')
            entry = KeybindEntry(main_frame, width=20)
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entries[action] = entry

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, columnspan=2, pady=10)  # Row after last keybind entry
        ttk.Button(button_frame, text="Save", command=self._save).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side='left', padx=5)

    def _load_current(self):
        for action, entry in self.entries.items():
            entry.set_bind(self.keybind_manager.keybinds[action])

    def _save(self):
        new_binds = {action: entry.get_bind() for action, entry in self.entries.items()}
        self.keybind_manager.save_keybinds(new_binds)
        self.destroy()

    def _validate_bind(self, bind_str):
        """Ensure valid Tkinter binding format"""
        # Handle standalone special characters
        if len(bind_str) == 1 and not bind_str.isalnum():
            return f"<{bind_str}>"
        
        # Clean up malformed brackets
        if not bind_str.startswith('<') or not bind_str.endswith('>'):
            cleaned = bind_str.strip('<>')
            return f"<{cleaned}>"
        
        return bind_str
    
class KeybindEntry(ttk.Entry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, state='readonly')
        self.current_bind = ''
        self.bind('<Button-1>', self._start_listening)
        self.listening = False

    def _start_listening(self, event):
        if self.listening:
            return
            
        self.listening = True
        self.config(state='normal')
        self.delete(0, 'end')
        self.insert(0, 'Press NEW keys (1 sec)...')
        self.config(state='readonly')
        
        # Cancel any previous key reg
        keyboard.unhook_all()
        keyboard.start_recording()
        
        # Capture fresh keys
        self.master.after(1000, self._process_recorded)

    def _process_recorded(self):
        pressed = keyboard.stop_recording()
        new_keys = []
        seen = set()
        
        for event in pressed:
            if event.event_type == 'down' and event.name not in seen:
                seen.add(event.name)
                new_keys.append(event.name)
                
        clean_bind = '+'.join(new_keys).lower()
        self.set_bind(clean_bind)
        self.listening = False

    def set_bind(self, value):
        self.current_bind = value
        self.config(state='normal')
        self.delete(0, 'end')
        self.insert(0, value.replace('_', '+'))  # Fix Windows key formatting
        self.config(state='readonly')

    def get_bind(self):
        return self.current_bind
