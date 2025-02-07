import json
from pathlib import Path
from tkinter import ttk, messagebox, Toplevel, Event
import keyboard
import tkinter as tk
import pystray
from PIL import Image
import io

DEFAULT_KEYBINDS = {
    'record': ['<control-r>'],
    'analyze': ['<control-a>']
}

class KeybindManager:
    def __init__(self, config_path='keybinds.config'):
        self.config_path = Path(config_path)
        self.keybinds = self._load_keybinds()
        self._callbacks = []
        self.hotkey_handles = {}
        self.root = None
    
    def add_callback(self, callback):
        self._callbacks.append(callback)
    
    def _register_hotkeys(self):
        # Unregister existing hotkeys
        for handle in self.hotkey_handles.values():
            keyboard.remove_hotkey(handle)
            
        try:
            # Add suppress=True to prevent event propagation
            self.hotkey_handles['record'] = keyboard.add_hotkey(
                self._format_hotkey(self.keybinds['record'][0]),
                self._trigger_record,
                suppress=True  # Prevent OS from handling the keypress
            )
            self.hotkey_handles['analyze'] = keyboard.add_hotkey(
                self._format_hotkey(self.keybinds['analyze'][0]),
                self._trigger_analyze,
                suppress=True
            )
        except Exception as e:
            print(f"Error registering hotkeys: {e}")

    
    def _format_hotkey(self, tk_bind):
        """Convert Tkinter bind format to keyboard lib format"""
        clean = tk_bind.strip('<>').replace('-', '+')
        return clean.lower()
    
    def _trigger_record(self):
        # Thread-safe GUI update
        self.root.event_generate("<<RecordTriggered>>")
    
    def _trigger_analyze(self):
        self.root.event_generate("<<AnalyzeTriggered>>")

    def notify_callbacks(self):
        for callback in self._callbacks:
            callback()
    
    def _load_keybinds(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    # Ensure proper formatting of modifiers
                    return {k: [self._format_bind(b) for b in v] 
                           for k, v in loaded.items()}
            return DEFAULT_KEYBINDS.copy()
        except Exception:
            return DEFAULT_KEYBINDS.copy()
    
    def _format_bind(self, bind_str):
        """Ensure modifier keys use correct capitalization"""
        modifiers = ['Control', 'Shift', 'Alt', 'Win']
        for mod in modifiers:
            if mod.lower() in bind_str.lower():
                bind_str = bind_str.replace(mod.lower(), mod)
        return bind_str
    
    def save_keybinds(self, keybinds):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(keybinds, f, indent=2)
            return True
        except Exception:
            return False

class KeybindDialog(Toplevel):
    def __init__(self, parent, keybind_manager):
        super().__init__(parent)
        self.title("Keybind Settings")
        self.configure(bg='#2d2d2d')
        self.keybind_manager = keybind_manager
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        
        self._create_widgets()
        self._load_current()
        self._setup_bindings()

    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(padx=10, pady=10)
        
        ttk.Label(main_frame, text="Record Key:").grid(row=0, column=0, sticky='w')
        self.record_entry = KeybindEntry(main_frame, width=20)
        self.record_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(main_frame, text="Analyze Key:").grid(row=1, column=0, sticky='w')
        self.analyze_entry = KeybindEntry(main_frame, width=20)
        self.analyze_entry.grid(row=1, column=1, padx=5, pady=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self._save).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side='left', padx=5)

    def _setup_bindings(self):
        self.bind('<FocusOut>', lambda e: self.focus_force())

    def _load_current(self):
        self.record_entry.set_bind(self.keybind_manager.keybinds['record'][0])
        self.analyze_entry.set_bind(self.keybind_manager.keybinds['analyze'][0])

    def _save(self):
        new_binds = {
            'record': [self._validate_bind(self.record_entry.get_bind())],
            'analyze': [self._validate_bind(self.analyze_entry.get_bind())]
        }
        if self.keybind_manager.save_keybinds(new_binds):
            self.keybind_manager.notify_callbacks()  # Trigger live update
            self.destroy()

    def _validate_bind(self, bind_str):
        """Ensure valid Tkinter binding format"""
        if not bind_str.startswith('<') or not bind_str.endswith('>'):
            return f"<{bind_str.strip('<>')}>"
        return bind_str

class KeybindEntry(ttk.Entry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_bind = ''
        self.modifiers = {
            'Control': False,
            'Shift': False, 
            'Alt': False
        }
        self.config(state='readonly')
        
        self.bind('<KeyPress>', self._update_modifiers_press)
        self.bind('<KeyRelease>', self._update_modifiers_release)
        self.bind('<FocusIn>', self._reset_modifiers)

    def _reset_modifiers(self, event=None):
        for key in self.modifiers:
            self.modifiers[key] = False

    def _update_modifiers_press(self, event):
        key = event.keysym
        if key.startswith('Control'):
            self.modifiers['Control'] = True
        elif key.startswith('Shift'):
            self.modifiers['Shift'] = True
        elif key.startswith('Alt'):
            self.modifiers['Alt'] = True
        else:
            self._process_key(event)

    def _update_modifiers_release(self, event):
        key = event.keysym
        if key.startswith('Control'):
            self.modifiers['Control'] = False
        elif key.startswith('Shift'):
            self.modifiers['Shift'] = False 
        elif key.startswith('Alt'):
            self.modifiers['Alt'] = False

    def _process_key(self, event):
        # Skip processing modifier-only presses
        if event.keysym in ['Control_L', 'Control_R', 'Shift_L', 'Shift_R', 'Alt_L', 'Alt_R']:
            return

        active_mods = [k for k,v in self.modifiers.items() if v]
        key = event.keysym
        
        if active_mods:
            bind_str = f"<{'-'.join(active_mods + [key]).lower()}>"
        else:
            bind_str = f"<{key.lower()}>" if len(key) > 1 else key.lower()

        self.set_bind(bind_str)
        self.master.focus_set()

    def set_bind(self, value):
        self.current_bind = value
        self.config(state='normal')
        self.delete(0, 'end')
        self.insert(0, value)
        self.config(state='readonly')

    def get_bind(self):
        return self.current_bind
