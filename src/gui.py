import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkhtmlview import HTMLScrolledText 
import markdown2
import threading
from loguru import logger
from src.gpt_query import transcribe_audio, generate_answer, generate_image_answer
from src.config import *
from src.audio import AudioRecorder
from src.keybinds import KeybindManager, KeybindDialog
import pystray
from PIL import Image, ImageGrab, ImageTk
from io import BytesIO
import base64
import win32gui

class InterviewGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("( > w < ; )")
        self.keybind_manager = KeybindManager()
        self.keybind_manager.callbacks.append(self._handle_hotkey)
        self._configure_window()
        self._setup_state()
        self._create_widgets()
        self._create_tray_icon()
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
        if not hasattr(self, 'tray_icon'):
            img = Image.new('RGB', (64, 64), '#2d2d2d')
            self.tray_icon = pystray.Icon(
                "interview_app",
                img,
                "( > w < ; )",
                pystray.Menu(
                    pystray.MenuItem('Open', self._show_window),
                    pystray.MenuItem('Exit', self.on_close)
                )
            )

    def _create_tray_menu(self):
        return pystray.Menu(
            pystray.MenuItem('Open', self._show_window),
            pystray.MenuItem('Exit', self.on_close)
        )
        
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
        self.record_btn = ttk.Button(control_frame, text="⏺ Record Audio", 
                                command=self.toggle_recording)
    
        self.analyze_audio_btn = ttk.Button(control_frame, text="🔍 Analyze Audio",
                                        command=self.start_audio_analysis)
        
        self.analyze_screenshot_btn = ttk.Button(control_frame, text="🖼 Analyze Screenshot",
                                                command=self.start_screenshot_analysis)
        
        self.record_btn.pack(side='left', padx=5)
        self.analyze_audio_btn.pack(side='left', padx=5)
        self.analyze_screenshot_btn.pack(side='left', padx=5)
        
        # Model Selection
        ttk.Label(control_frame, text="Model: ").pack(side='left', padx=(10, 0))
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

    def _handle_hotkey(self, action):
        handler = {
            'record': self.toggle_recording,
            'analyze_audio': self.start_audio_analysis,
            'analyze_screenshot': self.start_screenshot_analysis,
            'screenshot': self.take_screenshot
        }
        if handler := handler.get(action):
            handler()
        else:
            logger.warning(f"Unknown action: {action}")

    def take_screenshot(self):
        try:
            success = self.capture_focused_window()
            if success:
                logger.info("Saved screenshot.png")
            else:
                logger.error("Failed to capture window")
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
    
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

    def start_audio_analysis(self):
        self._update_markdown(self.question_view, "*Transcribing audio...*")
        threading.Thread(target=self._full_audio_analysis_pipeline).start()

    def start_screenshot_analysis(self):
        if not os.path.exists("screenshot.png"):
            logger.error("No screenshot found")
            return
            
        self._update_markdown(self.question_view, "*Analyzing screenshot...*")
        threading.Thread(target=self._full_screenshot_analysis_pipeline).start()

    def _full_screenshot_analysis_pipeline(self):
        try:
            self._display_screenshot("screenshot.png")
            position = self.position_entry.get()
            model = self.model_var.get()
            
            short_answer = generate_image_answer(
                "screenshot.png",
                short_answer=True,
                model=model,
                position=position
            )
            
            full_answer = generate_image_answer(
                "screenshot.png",
                short_answer=False,
                model=model,
                position=position
            )
            
            self._update_markdown(self.short_answer_view, short_answer)
            self._update_markdown(self.full_answer_view, full_answer)
            
        except Exception as e:
            logger.error(f"Screenshot analysis failed: {e}")
            self._update_markdown(self.question_view, "Analysis failed - check logs")

    def _full_audio_analysis_pipeline(self):
        transcript = transcribe_audio(OUTPUT_FILE_NAME)
        self._display_transcript(transcript)
        
        position = self.position_entry.get()
        model = self.model_var.get()
        
        self._generate_answers(transcript, position, model)

    def _display_transcript(self, text):
        self._update_markdown(self.question_view, text)

    def _display_screenshot(self, image_path):
        """Display thumbnail in question pane"""
        try:
            self._update_markdown(self.short_answer_view, "Generating short answer...")
            self._update_markdown(self.full_answer_view, "Generating detailed answer...")

            # Create thumbnail
            img = Image.open(image_path)
            img.thumbnail((300, 300))
            
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Create HTML with image
            html_content = f"""
                <img src="data:image/png;base64,{img_str}" 
                        style="max-width: 300px; margin: 10px 0; border-radius: 5px; border: 1px solid #454545">
            """
            self._update_markdown(self.question_view, html_content, is_html=True)
            
        except Exception as e:
            logger.error(f"Failed to display screenshot: {e}")
            self._update_markdown(self.question_view, "*Loaded screenshot*")

    def _generate_answers(self, transcript, position, model):
        self._update_markdown(self.short_answer_view, "Generating short answer...")
        self._update_markdown(self.full_answer_view, "Generating detailed answer...")
        
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

    def capture_focused_window(self):
        """Simplified screenshot capture"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return False
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            ImageGrab.grab((left, top, right, bottom)).save("screenshot.png")
            return True
        except Exception as e:
            logger.error(f"Screenshot failed: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"Screenshot failed: {str(e)}")
            return False

    def _update_markdown(self, widget, content, is_html=False):
        """Updated to handle HTML input"""
        full_html = f"""
            <span style="color: white; 
            font-family: Georgia, serif;
            font-size: 10px">
                {content if is_html else markdown2.markdown(content, extras=["fenced-code-blocks", "code-friendly"])}
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
