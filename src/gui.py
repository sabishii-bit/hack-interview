import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkhtmlview import HTMLScrolledText 
import markdown2
import threading
from loguru import logger
from src.gpt_query import transcribe_audio, generate_answer
from src.config import *
from src.audio import AudioRecorder
from src.keybinds import KeybindManager, KeybindDialog
import pystray
from PIL import Image


class InterviewGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("( > w < ; )")
        self.keybind_manager = KeybindManager()
        self.keybind_manager.add_callback(self._update_bindings)
        self._configure_window()
        self._setup_state()
        self._create_widgets()
        self._setup_bindings()
        self._create_tray_icon()
        self._setup_tray_bindings()
        self.audio = AudioRecorder()
        self.tray_active = False
        self.tray_lock = threading.Lock()

    def _configure_window(self):
        self.root.geometry("1000x800")
        self.root.configure(bg='#2d2d2d')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configure_styles()

    def _setup_state(self):
        self.is_recording = False
        self.audio_frames = []
        self.current_position = DEFAULT_POSITION

    def _create_tray_icon(self):
        # Create tray icon if not exists
        if not hasattr(self, 'tray_icon'):
            img = Image.new('RGB', (64, 64), '#2d2d2d')
            self.tray_icon = pystray.Icon(
                "interview_app",
                img,
                "( > w < ; )",
                self._create_tray_menu()
            )

    def _create_tray_menu(self):
        return pystray.Menu(
            pystray.MenuItem('Open', self._show_window),
            pystray.MenuItem('Exit', self.on_close)
        )
    
    def _setup_tray_bindings(self):
        self.root.bind("<<RecordTriggered>>", lambda e: self.toggle_recording())
        self.root.bind("<<AnalyzeTriggered>>", lambda e: self.start_analysis())
        
    def _hide_to_tray(self):
        with self.tray_lock:
            if not self.tray_active:
                self.root.withdraw()
                self.tray_active = True
                # Don't use run_detached - just update visibility
                if not self.tray_icon._running:
                    threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
    def _show_window(self):
        with self.tray_lock:
            if self.tray_active:
                self.root.deiconify()
                self.tray_active = False
                # Don't stop the icon, just hide the window

    def _configure_styles(self):
        bg_color = "#2d2d2d"
        text_color = "#ffffff"
        # Configure root element backgrounds
        self.root.configure(bg=bg_color)
        
        # Style base elements (match to main theme)
        self.style.configure('.', 
                            background=bg_color,
                            foreground=text_color)
        self.style.configure('TFrame', background=bg_color)
        self.style.configure('TButton', 
                          background='#404040', 
                          foreground=text_color,
                          padding=6)
        self.style.map('TButton', background=[('active', '#505050')])
        self.style.configure('TLabel', background=bg_color, foreground=text_color)
        self.style.configure('TEntry', fieldbackground='#FFFFFF', foreground="#000000")
        self.style.configure('TCombobox', fieldbackground='#FFFFFF', foreground="#000000")
        self.style.configure('Settings.TButton', 
                        background='#505050',
                        font=('Helvetica', 10))
        self.style.map('Settings.TButton',
                    background=[('active', '#606060')])

        # Handle sash (divider) elements
        self.style.configure('Sash',
                            gripcount=0,
                            width=3,
                            background='#404040',
                            troughcolor=bg_color)
        
        # Force dark sash style for paned windows
        self.style.layout('TPanedWindow',
                        [('Sash.horizontal', {'sticky': 'nswe'})])

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Control Panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=10)
        
        # Left-aligned controls
        self.record_btn = ttk.Button(control_frame, text="⏺ Start Recording", 
                                    command=self.toggle_recording)
        self.record_btn.pack(side='left', padx=5)
        
        self.analyze_btn = ttk.Button(control_frame, text="🔍 Analyze",
                                    command=self.start_analysis)
        self.analyze_btn.pack(side='left', padx=5)
        
        # Model Selection
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.model_combo = ttk.Combobox(control_frame, 
                                    textvariable=self.model_var,
                                    values=MODELS,
                                    state="readonly")
        self.model_combo.pack(side='left', padx=5)
        
        # Position Input with label
        ttk.Label(control_frame, text="Subject: ").pack(side='left', padx=(10, 0))
        self.position_entry = ttk.Entry(control_frame, width=25)
        self.position_entry.insert(0, self.current_position)
        self.position_entry.pack(side='left', padx=(0, 10))
        
        # Right-aligned settings button
        self.settings_btn = ttk.Button(control_frame, text="⚙", 
                                    command=self._open_settings,
                                    width=3)
        self.settings_btn.pack(side='right', padx=5)
        
        # HTML Panels
        self._create_content_panes(main_frame)


    def _create_content_panes(self, parent):
        # Main horizontal paned window
        main_pane = ttk.PanedWindow(parent, orient='horizontal')
        main_pane.pack(fill='both', expand=True)
        
        # Left column (20% width)
        left_pane = ttk.PanedWindow(main_pane, orient='vertical', width=350)
        
        # Question Panel (20% height of left pane)
        self.question_view = HTMLScrolledText(left_pane, height=5, background="#1e1e1e")  # Absolute minimum height
        left_pane.add(self.question_view, weight=1)  # 1 part
        
        # Short Answer Panel (80% height of left pane)
        self.short_answer_view = HTMLScrolledText(left_pane, background="#1e1e1e")
        left_pane.add(self.short_answer_view, weight=4)  # 4 parts
        
        # Add left pane to main with 20% width
        main_pane.add(left_pane, weight=1)  # 1 part of total width
        
        # Long Answer Panel (80% width)
        self.full_answer_view = HTMLScrolledText(main_pane, background="#1e1e1e")
        main_pane.add(self.full_answer_view, weight=4)  # 4 parts of total width
        
        # Force initial size constraints
        self.root.update_idletasks()
        left_pane.pane(0, weight=1)  # Question pane
        left_pane.pane(1, weight=4)  # Short answer
        main_pane.pane(0, weight=1)  # Left column
        main_pane.pane(1, weight=4)  # Right column
        
        self._initialize_content_views()

    def _initialize_content_views(self):
        # Initialize with empty styled content
        initial_html = """
        """
        for view in [self.question_view, self.short_answer_view, self.full_answer_view]:
            view.set_html(initial_html)
                
    def _update_bindings(self):
            """Update bindings without restart"""
            self.keybind_manager.keybinds = self.keybind_manager._load_keybinds()
            self.keybind_manager._register_hotkeys() 
            
            # Apply new binds
            self.root.bind(
                self.keybind_manager.keybinds['record'][0],
                lambda e: self.toggle_recording()
            )
            self.root.bind(
                self.keybind_manager.keybinds['analyze'][0], 
                lambda e: self.start_analysis()
            )
    
    def _setup_bindings(self):
        self._update_bindings()  # Initial setup
    
    def _open_settings(self):
        """Show keybind settings dialog"""
        KeybindDialog(self.root, self.keybind_manager)
        
    def toggle_recording(self):
            if self.audio.is_recording:
                self.audio.stop_recording()
                self.record_btn.config(text="⏺ Start Recording")
            else:
                self.audio.start_recording()
                self.record_btn.config(text="⏹ Stop Recording")

    def _record_audio(self):
        try:
            self.audio.start_recording()  # Starts async recording
            while self.audio.is_recording:  # Wait while recording
                self.root.update()  # Keep GUI responsive
                time.sleep(0.1)  # Prevent busy wait
        except Exception as e:
            logger.error(f"Recording error: {e}")
            self.audio.stop_recording()

    def start_analysis(self):
        self._update_markdown(self.question_view, "*Transcribing audio...*")
        threading.Thread(target=self._full_analysis_pipeline).start()

    def _full_analysis_pipeline(self):
        transcript = transcribe_audio(OUTPUT_FILE_NAME)
        self._display_transcript(transcript)
        
        position = self.position_entry.get()
        model = self.model_var.get()
        
        self._generate_answers(transcript, position, model)

    def _display_transcript(self, text):
        self._update_markdown(self.question_view, text)

    def _generate_answers(self, transcript, position, model):
        self._update_markdown(self.short_answer_view, "_Generating short answer..._")
        self._update_markdown(self.full_answer_view, "_Generating detailed answer..._")
        
        short_answer = generate_answer(
            transcript, 
            short_answer=True,
            model=model,
            position=position
        )
        
        full_answer = generate_answer(
            transcript,
            short_answer=False,
            model=model,
            position=position
        )
        
        self._update_markdown(self.short_answer_view, short_answer)
        self._update_markdown(self.full_answer_view, full_answer)

    def _update_markdown(self, widget, markdown_content):
        # Convert markdown to HTML with proper styling
        sanitized = markdown_content.replace("<", "&lt;").replace(">", "&gt;")
        html_content = markdown2.markdown(sanitized)
        full_html = f"""
        <span style="color: white; 
        font-family: Georgia, serif;
        font-size: 10px">
            {html_content}
        </span>
        """
        widget.set_html(full_html)
        widget.see("end")

    def on_close(self):
        logger.info("Full shutdown initiated")
        # Clean up audio resources
        try:
            self.audio.stop_recording()
        except Exception as e:
            logger.error(f"Audio cleanup error: {e}")
        
        # Terminate system tray
        try:
            if self.tray_icon:
                logger.debug("Stopping tray icon")
                self.tray_icon.stop()
        except Exception as e:
            logger.error(f"Tray cleanup error: {e}")
        
        # Destroy Tk root
        try:
            if self.root:
                logger.debug("Destroying root window")
                self.root.quit()  # Stop mainloop()
                self.root.destroy()
        except Exception as e:
            logger.error(f"Window cleanup error: {e}")
        
        # Force exit Python process
        logger.debug("Terminating Python process")
        os._exit(0)  # Direct exit, not sys.exit()

    def run(self):
        self.keybind_manager.root = self.root
        self.keybind_manager._register_hotkeys()
        
        # Start tray icon in a DAEMON thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
        # Run the main Tkinter event loop
        self.root.mainloop()
