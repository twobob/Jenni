import os
import re
import vlc
import wave
import pygame
import sv_ttk
import chardet
import threading
import subprocess
import numpy as np
import jenni_tooltip
import tkinter as tk
from pygame import mixer
from tkinter import messagebox
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from jenni_utils import find_matching_index
#from jenni_wave import make_wav_from_prompt
from tkinter import filedialog, scrolledtext, ttk
from jenni_image import generate_image_from_prompt_file_and_return_filepath, make_image_and_return_filepath
from jenni_story_splitter import story_split, find_all_story_files, find_all_story_files_without_sentence_files


# Set the SDL_VIDEODRIVER environment variable to 'dummy' before initializing Pygame
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()  # This now initializes all modules with a dummy video driver

# Initialize the mixer separately if needed (it's not)
#pygame.mixer.init()

# Function to handle mouse wheel scrolling
def on_mousewheel(event):
    app.label_canvas.yview_scroll(int(-1*(event.delta/60)), "units")

class App(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sv_ttk.set_theme('dark')

        # Default directory
        self.default_directory = r"C:\Users\new\LMStudio_StoryTalk\projects\20240101_034619API-gpt-4\rendered_sentences"

        self.minsize(width=800, height=580)

        self.spectrogram_file = None
        self.wave_file = None
        self.mp4_file = None
        self.mp4_playlist = None
        self.sentence_file = None
        self.sentence_files = None

        self.current_image = None
        self.photo = None

        self.checkboxes = {}
        self.tooltips = {}  # Dictionary to store tooltip objects     
        self.label_tooltip_map = {}  # Dictionary to map labels to tooltips

        self.pipe = "NotSet"
        
        self.txt_files = []
        
        self.prompt = ""

        self.selected_records = []

        self.playlist = None#  POPULATE THIS WHEN WE CAN for a wav / mp4 playlist  # A list of music file paths
        self.current_song_index = 0

        self.logging = False
      
        # Configure the rows and columns of the main grid
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=0, minsize=25)  # Toolbar should stay fixed height
        self.rowconfigure(1, weight=1, minsize=100)  # Second row should grow and have a minimum size

        self.button_y_padding = 5


        # Toolbar frame that runs across the top
        self.alert_frame = tk.Frame(self, height=40, bg='gray')  # Set the desired height and background color
        self.alert_frame.grid(row=0, column=0, sticky=tk.NW, columnspan=3)  # Span across all the columns you have

        self.create_checkboxes(['Make Image', 'Make Wave', 'Make Video'], frame=self.alert_frame)

        # Toolbar frame that runs across the top
        #self.artist_frame = tk.Frame(self, height=40, bg='gray')  # Set the desired height and background color
        #self.artist_frame.grid(row=0, column=0, sticky=tk.N, columnspan=3)  # Span across all the columns you have

        self.artist_name_box = tk.Entry(self.alert_frame, width=100)
        self.artist_name_box.pack( side= tk.LEFT, padx=5) # row=0, column=0)
        self.artist_name_box.lower()
        self.artist_name_box.insert(0, "Hiroshi Sugimoto")  # Set the default value



        # Toolbar frame that runs across the top
        self.toolbar_frame = tk.Frame(self, height=40, bg='gray')  # Set the desired height and background color
        self.toolbar_frame.grid(row=0, column=0, sticky=tk.NE, columnspan=3)  # Span across all the columns you have
        self.toolbar_frame.lift()

        self.create_checkboxes(['Autoplay', 'Video/Image', 'Logging'], frame=self.toolbar_frame)



        # Left column frame for media players
        self.left_frame = tk.Frame(self)
        self.left_frame.grid(column=0, row=1, sticky="nsew")
        self.left_frame.columnconfigure(0, weight=1, minsize=300) 
        self.left_frame.rowconfigure(0, weight=1, minsize=300)   # Video player row
        self.left_frame.rowconfigure(1, weight=1)  # Wave row
        self.left_frame.rowconfigure(2, weight=1)  # Spectrogram row

        # Right column frame for text editor and controls
        self.right_frame = tk.Frame(self)
        self.right_frame.grid(column=1, row=1, sticky="nsew")
        self.right_frame.columnconfigure(0, weight=2)

        # Configure the right frame's grid to give more space to the labels than the text editor
        self.right_frame.rowconfigure(0, weight=0)  # Give less weight to the text editor
        self.right_frame.rowconfigure(1, weight=0)  # Fixed space for the editor controls
        self.right_frame.rowconfigure(2, weight=1)  # Give more weight to the labels frame, making it take more space

        # Initialize VLC
        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()

        # Create a frame for the VLC player
        self.video_frame = tk.Frame(self.left_frame, background="#202020")
        self.video_frame.grid(column=0, row=0, sticky="nsew", padx=5, pady=5)
        self.video_frame.bind("<Configure>", self._resize_video_frame)
        self.video_frame.lower()

        # Create a frame for the image display
        self.image_frame = tk.Frame(self.left_frame, background="red")# background="#202020")
        self.canvas = tk.Canvas(self.image_frame, width=300, height=300, background="green")
        self.canvas.pack(fill="both", expand=True)
        self.image_frame.grid(column=0, row=0, sticky="nsew", padx=5, pady=5)
        # Create a canvas to display the image
        # self.image_frame.lower()
        # Bind the resize event
        self.canvas.bind("<Configure>", self.resize_display)     

        self.clear_button = ttk.Button(self.left_frame, text="REGENERATE", command=lambda : self.generate_image(None, self.current_image.filename if isinstance(self.current_image, Image.Image) else self.current_image))
        self.clear_button.grid(column=0, row=0, sticky= tk.S, padx=2, pady=self.button_y_padding)
        self.clear_button.lift()

        # Create a frame for the wave images and configure it to expand
        self.wave_frame = tk.Frame(self.left_frame, background="black")
        self.wave_frame.grid(column=0, row=1, sticky="nsew", padx=5, pady=5)
        self.wave_frame.columnconfigure(0, weight=1)  # Make the frame expandable
        self.wave_frame.rowconfigure(0, weight=1)  # Make the frame expandable
        self.wave_label = tk.Label(self.wave_frame)
        self.wave_label.pack(fill="both", expand=True)  # Make the label expandable

        #Create a frame for spectrogram images and configure it to expand
        self.spectrogram_frame = tk.Frame(self.left_frame, background="black")
        self.spectrogram_frame.grid(column=0, row=2, sticky="nsew", padx=5, pady=5)
        self.spectrogram_frame.columnconfigure(0, weight=1)  # Make the frame expandable
        self.spectrogram_frame.rowconfigure(0, weight=1)  # Make the frame expandable
        self.spectrogram_label = tk.Label(self.spectrogram_frame)
        self.spectrogram_label.pack(fill="both", expand=True)  # Make the label expandable
            
        # Text editor area now with less space (smaller)
        self.editor = scrolledtext.ScrolledText(self.right_frame, height=5)  # Adjust the height as needed
        self.editor.grid(column=0, row=0, sticky="nsew", padx=5, pady=5)

        # Control buttons for the text editor
        self.editor_controls_frame = ttk.Frame(self.right_frame)
        self.editor_controls_frame.grid(column=0, row=1, sticky="ew", padx=5, pady=5)
        self.editor_controls_frame.columnconfigure((0, 1, 2, 3), weight=1)

        # Buttons for CLEAR, RELOAD, SAVE, and Choose Folder
        self.clear_button = ttk.Button(self.editor_controls_frame, text="CLEAR", command=self.clear_editor)
        self.reload_button = ttk.Button(self.editor_controls_frame, text="RELOAD", command=self.reload_editor)
        self.save_button = ttk.Button(self.editor_controls_frame, text="SAVE", command=self.save_editor)
        self.choose_dir_button = ttk.Button(self.editor_controls_frame, text="Choose Folder", command=self.choose_directory)

        pause_char = chr(0x23F8)
        stop_char = chr(0x23F9)
        play_char = chr(0x23F5)

        #self.browse_button = tk.Button(self, text="Browse", command=self.browse_file)
        self.pause_button = tk.Button(self.editor_controls_frame, text=f"{pause_char} Pause", command=self.pause_file)
        self.resume_button = tk.Button(self.editor_controls_frame, text="REGENERATE", foreground="darkred", command=lambda : self.make_waves(self.wave_file))
        self.stop_button = tk.Button(self.editor_controls_frame, text=f"{stop_char} Stop", command=self.stop_file)
        self.play_button = tk.Button(self.editor_controls_frame, text=f"{play_char} Play", command=self.play_file)       


        #self.browse_button.grid(column=0, row=0, sticky="nsew", padx=2, pady=2)
        self.pause_button.grid(column=1, row=1, sticky="nsew", padx=2, pady=self.button_y_padding)
        self.resume_button.grid(column=3, row=1, sticky="nsew", padx=2, pady=self.button_y_padding)
        self.stop_button.grid(column=2, row=1, sticky="nsew", padx=2, pady=self.button_y_padding)
        self.play_button.grid(column=0, row=1, sticky="nsew", padx=2, pady=self.button_y_padding)

        self.clear_button.grid(column=0, row=0, sticky="nsew", padx=2, pady=self.button_y_padding)
        self.reload_button.grid(column=1, row=0, sticky="nsew", padx=2, pady=self.button_y_padding)
        self.save_button.grid(column=2, row=0, sticky="nsew", padx=2, pady=self.button_y_padding)
        self.choose_dir_button.grid(column=3, row=0, sticky="nsew", padx=2, pady=self.button_y_padding)

        # Directory chooser initialization
        self.directory = self.default_directory

        # Labels frame now with more space (larger), potentially swapped position with text editor
        self.labels_frame = ttk.Frame(self.right_frame)
        self.labels_frame.grid(column=0, row=2, sticky="nsew", padx=5, pady=5)  # If swapping, change row from 2 to 0

        self.labels = []
        
        # Scrollable canvas for labels
        self.label_canvas = tk.Canvas(self.labels_frame)
        self.scrollbar = ttk.Scrollbar(self.labels_frame, command=self.label_canvas.yview)
        self.label_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.label_canvas.pack(side="left", fill="both", expand=True)
        
        self.label_canvas_frame = ttk.Frame(self.label_canvas)
        self.label_canvas.create_window((0, 0), window=self.label_canvas_frame, anchor='nw')
        self.label_canvas_frame.bind("<Configure>", lambda e: self.label_canvas.configure(scrollregion=self.label_canvas.bbox("all")))

        # Bind mouse wheel scroll event
        self.bind_all("<MouseWheel>", on_mousewheel)

        # init the labels
        self.parse_txt_files()


    def make_waves(self, file_name):
        for prompt in self.selected_records:
            mixer.music.unload()
            subprocess.run(["C:/Users/new/122/Scripts/python.exe", "jenni_wave.py", prompt.cget("text").strip("[]'").split(':', 1)[1].strip(), file_name, self.directory])
            mixer.music.load(file_name)
            mixer.music.play()
            #self.play_media(self.selected_records.index(prompt))


    def play_next_video(self):
        while self.vlc_player.is_playing():
            pass
        if self.current_song_index < len(self.playlist):
            self.highlight_label_Load_text_Increment_song_Index()
            index_in_other_list = find_matching_index(self.playlist, self.mp4_playlist, self.current_song_index)
            if index_in_other_list > -1:
                self.mp4_file = self.mp4_playlist[index_in_other_list]
            else:
                self.mp4_file = None 
                self.wave_file = os.path.join(self.directory, self.playlist[self.current_song_index]   ) 
            self.play_file()   
            self.current_song_index += 1  

    def highlight_label_Load_text_Increment_song_Index(self):
        
        self.highlight_label(self.labels[self.current_song_index], event=None)            
        # Load text into editor
        self.load_text_into_editor(self.sentence_files[self.current_song_index])


    def play_next_song(self):

        while self.vlc_player.is_playing():
            pass
        if self.current_song_index < len(self.playlist):
            self.highlight_label_Load_text_Increment_song_Index()

            self.wave_file = os.path.join(self.directory, self.playlist[self.current_song_index]   ) 
            self.play_file()
            self.current_song_index += 1
            #    pygame.mixer.music.load(os.path.join(self.directory,self.playlist[self.current_song_index]))
            #    pygame.mixer.music.play()
            
        else:
            print("End of playlist")


    def check_for_song_end(self):
        if not self.vlc_player.is_playing():
            if self.mp4_file:
                self.play_next_video()  
            else:
                for event in pygame.event.get():
                    if event.type == SONG_END:
                        self.play_next_song()

    def create_checkboxes(self, checkbox_names, frame):
        """Create checkboxes in the toolbar frame and adorn them with tooltips."""
   
        for name in checkbox_names:
            var = tk.BooleanVar(value=True if name == "Video/Image" else False)
            cb = tk.Checkbutton(frame, text=name, variable=var, bg='gray', fg='black',
                                command=lambda n=name, v=var: self.click_checkbox(n, v))
            cb.pack(side='left', padx=10)
            self.checkboxes[name] = var
            self.tooltips[name] =  jenni_tooltip.ToolTip(cb, f"Show Image") if name == "Video/Image" else jenni_tooltip.ToolTip(cb, f"Toggle {name}")

    def click_checkbox(self, name, var):
        """Method called when a checkbox is clicked."""
        if self.logging:
            print(f"Checkbox '{name}' clicked, value is now: {var.get()}")
        if "Autoplay" in name:
            if var.get():
                if not self.selected_records:
                    self.select_file(self.txt_files[0], self.labels[0], None)
        if "Logging" in name:
            self.logging = var.get()
        if "Video/Image" in name:
            if var.get():
                self.tooltips[name].update_text("Show Video")
                self.video_frame.lower()
                self.image_frame.lift()
            else:
                self.tooltips[name].update_text("Show Image")
                self.video_frame.lift()
                self.image_frame.lower()


    # Method to update wave image
    def update_wave_image(self, image_path):
        wave_image = Image.open(image_path)
        wave_image.thumbnail((300, wave_image.height))        
        wave_photo = ImageTk.PhotoImage(wave_image)
        self.wave_label.config(image=wave_photo)
        self.wave_label.image = wave_photo  # Keep a reference!
        #wave_file = image_path

    # Method to update spectrogram image
    def update_spectrogram_image(self, image_path):
        spectrogram_image = Image.open(image_path)
        spectrogram_image.thumbnail((300, spectrogram_image.height)) 
        spectrogram_photo = ImageTk.PhotoImage(spectrogram_image)
        self.spectrogram_label.config(image=spectrogram_photo)
        self.spectrogram_label.image = spectrogram_photo  # Keep a reference!
        self.spectrogram_file = image_path

    def play_file(self):
        # Play video <-- PREFER VIDEO
        if self.mp4_file is not None and os.path.exists(self.mp4_file):
            media = self.vlc_instance.media_new(self.mp4_file)
            self.vlc_player.set_media(media)
        # Play audio
        elif self.wave_file is not None and os.path.exists(self.wave_file):
            mixer.music.load(self.wave_file)
            mixer.music.play()

        def delayed_playback():
            # Play video
            if self.mp4_file is not None and os.path.exists(self.mp4_file):
                self.vlc_player.play()
            # Play audio
            #elif self.wave_file is not None and os.path.exists(self.wave_file):
            #    mixer.music.play()

        # Delay playback by 300ms
        threading.Timer(.3, delayed_playback).start()

    def pause_file(self):
        if mixer.music.get_busy():
            mixer.music.pause()
        else:
            mixer.music.unpause()
        self.vlc_player.pause()

    #def resume_file(self):
    #    mixer.music.unpause()
    #    self.vlc_player.pause()

    def stop_file(self):
        mixer.music.stop()
        self.vlc_player.stop()

    # Function to unhighlight all labels and highlight the selected one
    def highlight_label(self, selected_label, event=None):
        self.current_song_index = self.labels.index(selected_label)

        # Access the tooltip text using the label
        text_file = self.label_tooltip_map[selected_label].text
        self.current_image = text_file.replace('.txt','.png')
        self.resize_and_display_image(self.current_image)
        if event is not None:
            # Check if Ctrl (Control_L or Control_R) or Shift (Shift_L or Shift_R) keys are held down
            ctrl_held = event.state & 0x4 != 0
            shift_held = event.state & 0x1 != 0
        else:
            shift_held = ctrl_held = 0    

        if not ctrl_held and not shift_held:
            for label in self.labels:
                label['bg'] = '#202020'  # Default background color
                label['fg'] = 'white'
            self.selected_records = []    
        self.selected_records.append(selected_label)        
        selected_label['bg'] = 'lightyellow'  # Highlight color
        selected_label['fg'] = '#202020' 

    def choose_directory(self):
        ## by default when we open the app they match
        if self.directory == self.default_directory:
            dirname = filedialog.askdirectory(initialdir=self.default_directory)
        else:
            dirname = filedialog.askdirectory(initialdir=self.directory)    
        if dirname:
            if "rendered_sentences" in dirname:
                self.directory = dirname
                self.parse_txt_files()
            else:
                self.warning_nonstandard()
                self.directory = dirname
                self.parse_txt_files(True)    

    def warning_nonstandard(self):
        messagebox.showwarning("NON-STANDARD FOLDER", "by default the sentence files should be in folders called rendered_sentences")

    def _resize_video_frame(self, event=None):
        width, height = self.video_frame.winfo_width(), self.video_frame.winfo_height()
        if self.vlc_player:
            self.vlc_player.set_hwnd(self.video_frame.winfo_id())
        


    def test_permission_then_split_files(self, directory = None):
        directory = self.directory if (directory is None) else directory
        # Create a YES/NO dialog
        user_choice = messagebox.askyesno("Confirmation", f"No sentence files are present in {directory}.\nDo you want to make them?")
        
        if user_choice:
            # User chose YES, proceed with the action
            # we found a story file in the parent directory and are making it there.
            if "rendered_sentences" in self.directory: 
                story_split(self.directory.replace('rendered_sentences',''))
            else:
                # we are in some other folder and are going to make them in the subdir as usual
                story_split(self.directory)
                self.directory = f"{self.directory}\\rendered_sentences"     
        else:
            # User chose NO, show a warning
            messagebox.showwarning("Warning", "Action aborted.")
        return user_choice


    def parse_txt_files(self, warned=False):
        # Clear the existing labels
        for label in self.labels:
            label.destroy()
        self.labels.clear()

        # Define the regex pattern for the .txt files
        txt_file_pattern = re.compile(r'sentence_\d+\.txt$')

        # Get the list of .txt files in the chosen directory that match the pattern
        self.txt_files = [f for f in os.listdir(self.directory) if txt_file_pattern.match(f)]
        ## do we already have the files in the place we would normally generate them
        if not len (self.txt_files):
            rendered_folder_exists = os.path.exists(f"{self.directory.replace('rendered_sentences','')}/rendered_sentences")
            if rendered_folder_exists:
                self.txt_files =    sub_txt_files =  [f for f in os.listdir(f"{self.directory.replace('rendered_sentences','')}\\rendered_sentences") if txt_file_pattern.match(f)]
                if len(self.txt_files):
                    self.directory = f"{self.directory}\\rendered_sentences"
        ## ACCOUNT FOR THE CASE WHERE WE DIDN'T MAKE THEM YET
        choice = True
        if not len(self.txt_files):
            stories = find_all_story_files_without_sentence_files(directory=self.directory.replace('rendered_sentences',''))
            # if we dont find any here and we ALREADY made them just go to the folder for the user
            if rendered_folder_exists and sub_txt_files:
                self.directory = f"{self.directory}\\rendered_sentences"
            ## only offer to split the files if we just got here via a folder selection and the folder contains a story file.
            elif (warned or "rendered_sentences" in self.directory) and stories :
                if len(stories) == 1:
                    choice = self.test_permission_then_split_files(self.directory)
                    # Get the list of .txt files in the chosen directory that match the pattern
                    self.txt_files = [f for f in os.listdir(self.directory) if txt_file_pattern.match(f)]
                if len(stories) > 1:
                    ## N.B. WE END UP IN THE LAST PROJECT RENDERED. OH WELL 
                    for story in stories:
                        self.directory = os.path.dirname(story)
                        choice = self.test_permission_then_split_files(self.directory)
                    self.txt_files = [f for f in os.listdir(self.directory) if txt_file_pattern.match(f)]
            else:
                if sub_txt_files:
                    self.txt_files = [f for f in os.listdir(self.directory) if txt_file_pattern.match(f)]
                else:    
                    self.warning_nonstandard()

        if choice and warned or len(self.txt_files):

            # Sort the list by extracting the numeric part of the filenames
            sorted_txt_files = sorted(self.txt_files, key=lambda x: int(re.search(r'\d+', x).group()))

            self.sentence_files = sorted_txt_files

            # Assuming 'sorted_txt_files' is already defined and contains the sorted .txt filenames
            self.playlist = [re.sub(r'\.txt$', '_edited.wav', txt_file) for txt_file in sorted_txt_files]

            self.mp4_playlist = [re.sub(r'\.txt$', '.mp4', txt_file) for txt_file in sorted_txt_files]

            # Create labels
            for txt_file in sorted_txt_files:
                content = self.prompt_from_txt_file(txt_file)
                label = tk.Label(self.label_canvas_frame, text=f"{txt_file.replace('sentence_','').replace('.txt','')}: {content}", anchor='w', justify='left')
                label.bind('<Button-1>', lambda e, lbl=label, txt=txt_file: self.select_file(txt, lbl, e))
                label.pack(fill='x')
                self.label_tooltip_map[label] = jenni_tooltip.ToolTip(label, txt_file)
                self.labels.append(label)

    def prompt_from_txt_file(self, file):
        file.replace('.png','.txt')
        file.replace('.wav','.txt')
        file.replace('_edited.wav','.txt')
        
        with open(os.path.join(self.directory, file), 'r') as file:
            return file.read().strip()

    def load_text_into_editor(self, txt_file=None):
        if txt_file is None:
            txt_file = self.sentence_file
        
        with open(os.path.join(self.directory, txt_file), 'r') as file:
            content = file.read()
        if not txt_file == self.sentence_file:
             self.sentence_file = txt_file 
        self.editor.delete('1.0', tk.END)
        self.editor.insert(tk.END, content)

        # Play corresponding audio and video files
        file_number = re.search(r'\d+', txt_file).group()

    def select_file(self, txt_file, lbl, event=None):

        self.highlight_label(lbl, event)

        # Load text into editor
        self.load_text_into_editor(txt_file)
        
        # Play corresponding audio and video files
        file_number = re.search(r'\d+', txt_file).group()
        self.play_media(file_number)

    def play_media(self, file_number):
        # Stop current media
        mixer.music.stop()
        self.vlc_player.stop()

        # Play audio
        spectrogram_image  = os.path.join(self.directory, f'sentence_{file_number}_spectrogram.png')
        wave_image  = os.path.join(self.directory, f'sentence_{file_number}_waveform.png')
        scene_image  = os.path.join(self.directory, f'sentence_{file_number}.png')

        self.wave_file = os.path.join(self.directory, f'sentence_{file_number}.wav')
        if not os.path.exists(self.wave_file ):
            self.wave_file = os.path.join(self.directory, f'sentence_{file_number}_edited.wav')
        if os.path.exists(self.wave_file ):
            with wave.open(self.wave_file , 'rb') as wav_obj:
                sample_freq = wav_obj.getframerate()
                n_samples = wav_obj.getnframes()
                t_audio = n_samples / sample_freq
                signal_wave = wav_obj.readframes(n_samples)
                signal_array = np.frombuffer(signal_wave, dtype=np.int16)

            if wav_obj.getnchannels() == 2:
                l_channel = signal_array[0::2]
                r_channel = signal_array[1::2]
            else:
                l_channel = signal_array
                r_channel = signal_array

            times = np.linspace(0, n_samples/sample_freq, num=n_samples)

            playhead_time = 0.0  # Replace with the desired time for the playhead indicator

            # Create the figure with a dark background
            fig, ax = plt.subplots(figsize=(15, 5), facecolor='#202020')
            ax.set_facecolor('#202020')  # Set the background color of the axes

            # Plot the waveform
            ax.plot(times, l_channel, color='lightyellow')

            # Add a playhead indicator
            ax.axvline(x=playhead_time, color='red', linestyle='--')

            # Set the title and labels with white color for contrast
            ax.set_title('Left Channel', color='white')
            ax.set_ylabel('Signal Value', color='white')
            ax.set_xlabel('Time (s)', color='white')

            # Set the limits for the x-axis
            ax.set_xlim(0, t_audio)

            # Set the color of the axes and ticks to white for visibility against the dark background
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')

            # Set the background color of the axes to black
            plt.gca().set_facecolor('#202020')

            # Save the figure with a dark background and no border
            plt.savefig(wave_image, facecolor='#202020', bbox_inches='tight', pad_inches=0, transparent=True)


            self.update_wave_image(wave_image)

            # end of wav

            # Create the figure with a dark background
            # Create the figure with a dark background
            fig_spectrogram, ax_spectrogram = plt.subplots(figsize=(15, 5), facecolor='#202020')
            ax_spectrogram.set_facecolor('#202020')  # Set the background color of the axes

            # Generate a spectrogram
            S, freqs, times, im = ax_spectrogram.specgram(l_channel, Fs=sample_freq, vmin=-20, vmax=50)

            # Set the title and labels with white color for contrast
            ax_spectrogram.set_title('Left Channel', color='white')
            ax_spectrogram.set_ylabel('Frequency (Hz)', color='white')
            ax_spectrogram.set_xlabel('Time (s)', color='white')

            # Set the limits for the x-axis and add the playhead indicator
            ax_spectrogram.set_xlim(0, t_audio)
            ax_spectrogram.axvline(x=playhead_time, color='red', linestyle='--')

            # Create a colorbar with a label
            cbar = fig_spectrogram.colorbar(im, ax=ax_spectrogram)
            cbar.set_label('Intensity (dB)', color='white')
            cbar.ax.yaxis.set_tick_params(color='white')
            cbar.outline.set_edgecolor('white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

            # Set the color of the axes and ticks to white for visibility against the dark background
            ax_spectrogram.spines['bottom'].set_color('white')
            ax_spectrogram.spines['top'].set_color('white')
            ax_spectrogram.spines['right'].set_color('white')
            ax_spectrogram.spines['left'].set_color('white')
            ax_spectrogram.tick_params(axis='x', colors='white')
            ax_spectrogram.tick_params(axis='y', colors='white')

            # Save the figure with a dark background and no border
            plt.savefig(spectrogram_image, facecolor='#202020', bbox_inches='tight', pad_inches=0, transparent=True)

            #plt.figure(figsize=(15, 5), facecolor='#202020')
            #plt.specgram(l_channel, Fs=sample_freq, vmin=-20, vmax=50)
            #plt.title('Left Channel')
            #plt.ylabel('Frequency (Hz)')
            #plt.xlabel('Time (s)')
            #plt.xlim(0, t_audio)
            #plt.colorbar()
            #plt.savefig(spectrogram_image)
            self.update_spectrogram_image(spectrogram_image)
            plt.close()
        # Play video
        self.mp4_file = os.path.join(self.directory, f'sentence_{file_number}.mp4')

        self.play_file()

    def clear_editor(self):
        self.editor.delete('1.0', tk.END)

    def reload_editor(self):
        self.load_text_into_editor()

    def save_editor(self):
        sentence_to_save = self.editor.get('1.0', tk.END)
        self.write_to_file(sentence_to_save, os.path.join(self.directory,self.sentence_file))
        #self.parse_txt_files()

    def write_to_file(self, sentence, file_path):
        # Detect the encoding of the sentence
        detected_encoding = chardet.detect(sentence.encode())['encoding']

        # List of valid encodings
        valid_encodings = ['utf-8', 'ascii', 'windows-1252']

        # Determine the encoding to use
        if detected_encoding not in valid_encodings:
            encoding_to_use = 'utf-8'
        else:
            encoding_to_use = detected_encoding

        # Try writing to file using the determined encoding
        try:
            with open(file_path, 'wb') as file:
                file.write(sentence.strip().encode(encoding_to_use))
            return f"File saved successfully with encoding: {encoding_to_use}"
        except UnicodeEncodeError:
            # If saving with the chosen encoding fails, try with windows-1252
            try:
                with open(file_path, 'wb') as file:
                    file.write(sentence.strip().encode('windows-1252'))
                return "File saved with fallback encoding: windows-1252"
            except UnicodeEncodeError:
                # If saving with the chosen encoding fails, try with windows-1252
                try:
                    with open(file_path, 'wb') as file:
                        file.write(sentence.strip().encode('ascii'))
                    return "File saved with fallback encoding: ascii"
                except UnicodeEncodeError:
                    return "Failed to save file with all three encodings."

    def handle_generate_button_click(self):
        if self.txt_files:
            # Extract the text from each label in self.selected_records
            selected_prompts = [label.cget("text") for label in self.selected_records]
            
            for file in self.txt_files:
                prompt = self.prompt_from_txt_file(file)
                # Check if the prompt is in the list of selected prompts
                if prompt in selected_prompts:
                    file_name = file.replace('.txt', '.png')
                    threading.Thread(target=self.generate_image, args=(prompt, file_name)).start()

    def generate_image(self, prompt, file_name):
        for prompt in self.selected_records:
            self.current_image, self.pipe = generate_image_from_prompt_file_and_return_filepath(
                os.path.join(self.directory, file_name), 
                file_name, 
                artist=self.artist_name_box.get(),
                pipe=self.pipe, 
                save_dir=self.directory)
            self.current_image = Image.open(os.path.join(self.directory,self.current_image.filename if isinstance(self.current_image, Image.Image) else self.current_image))

            #file_name = file_name.filename if isinstance(file_name, Image.Image) else file_name
            #passed_prompt = prompt.cget("text").strip("[]'").split(':', 1)[1].strip() if prompt is None or isinstance(prompt, tk.Label) else prompt
            #subprocess.run(["C:/Users/new/AppData/Local/Microsoft/WindowsApps/python.exe", "jenni_image.py", passed_prompt, file_name])
            self.load_and_display_image(self.current_image.filename)# file_name)

    def load_and_display_image(self,file_name):
        # Call the resize and display function
        self.current_image = file_name
        self.resize_and_display_image(file_name)

    def resize_display(self, event=None):
        if self.current_image is not None:
            # Check if self.current_image is an instance of Image
            if isinstance(self.current_image, Image.Image):
                # It's an Image, use its filename attribute
                self.resize_and_display_image(self.current_image.filename)
            elif isinstance(self.current_image, str):
                # It's a string, use it directly
                self.resize_and_display_image(self.current_image)

    def resize_and_display_image(self,file_name):
        if self.current_image is not None:
            try:
                file_exists = os.path.exists(os.path.join(self.directory, file_name))
                # Load the image from the file
                if file_exists:
                    self.current_image = Image.open(os.path.join(self.directory, file_name))
                else:
                    if self.checkboxes["Make Image"].get():
                        self.current_image, self.pipe = generate_image_from_prompt_file_and_return_filepath(
                            os.path.join(self.directory, file_name), 
                            file_name, 
                            artist=self.artist_name_box.get(),
                            pipe=self.pipe, 
                            save_dir=self.directory)

                        self.current_image = Image.open(os.path.join(self.directory,self.current_image))
                        file_exists = True
                if file_exists:        
                    if self.checkboxes["Video/Image"].get():
                        # Get canvas dimensions
                        canvas_width = self.canvas.winfo_width()
                        canvas_height = self.canvas.winfo_height()
                    else:
                        # Get video canvas dimensions
                        canvas_width = self.video_frame.winfo_width()
                        canvas_height = self.video_frame.winfo_height()                        

                    # Calculate the aspect ratio of the image
                    img_width, img_height = self.current_image.size
                    img_aspect = img_width / img_height

                    # Calculate aspect ratio of canvas
                    canvas_aspect = canvas_width / canvas_height

                    # Determine the appropriate resize dimensions
                    if img_aspect > canvas_aspect:
                        # Image is wider than the canvas
                        new_width = canvas_width
                        new_height = int(new_width / img_aspect)
                    else:
                        # Image is taller than the canvas
                        new_height = canvas_height
                        new_width = int(new_height * img_aspect)

                    # Resize the image to fit the canvas while maintaining aspect ratio
                    resized_image = self.current_image.resize((new_width, new_height))
                    photo = ImageTk.PhotoImage(resized_image)

                    # Clear the previous image and add new image to the canvas
                    self.canvas.delete("all")
                    
                    self.canvas.create_image(canvas_width / 2, canvas_height / 2, anchor='center', image=photo)
                    self.photo = photo
            except IOError:
                print("Error loading or resizing the image.")


    def mainloop(self):
        while True:
            if self.checkboxes["Autoplay"].get():
                self.check_for_song_end()
            try:
                # This ensures the Tkinter mainloop runs as well
                self.update()
                self.update_idletasks()
            except tk.TclError as e:  # Catch the exception when the window is closed
                pygame.mixer.music.stop()  # Stop the music when closing the app
                pygame.quit()  # Quit pygame
                break




#TODO vega #generate_image_save_and_return_filepath
#TODO regerate video
#TODO regenerate audio

mixer.music.get_endevent()

# Define a custom event for the end of a song
SONG_END = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(SONG_END)



if __name__ == "__main__":

    app = App()
    app.mainloop()
