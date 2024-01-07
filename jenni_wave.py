

# use pip to install torch nightly with cuda support
# install commands here https://pytorch.org/get-started/locally/
# example:  
# pip3 install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu121
#
# pip install nltk
# python -m nltk.downloader punkt

# pip install tqdm
# pip install pydub
# pip install pedalboard
# pip install TTS

# pip install soundfile
# pip install numpy
# pip install matplotlib
# pip install PyWavelets
# pip install noisereduce
# pip install chardet
# pip install anything else that complains about being missing when you first run this

from datetime import datetime
import nltk
from tqdm import tqdm
import gibberish_extractor
import os
from pydub import AudioSegment
import re
import subprocess
import os
import time
import torch
import sys

# Directory to be added
path_to_add = "nuwave2"

# Add the directory to sys.path
if path_to_add not in sys.path:
    sys.path.append(path_to_add)
import nuwave2
from nuwave2 import inference

from noise_reducer import clean_and_backup_audio
import chardet

################################################################################################################################



def convert_wav_to_mp3(wav_file, fx_file, mp3_file, folder='audio'):
    os.makedirs(folder, exist_ok=True)
    
    fx_file = os.path.join(folder, fx_file)
    mp3_file = os.path.join(folder, mp3_file)

    # Open an audio file for reading:
    with AudioFile(wav_file) as f:
    
        # Open an audio file to write to:
        with AudioFile(fx_file, 'w', f.samplerate, f.num_channels) as o:
        
            # Read one second of audio at a time, until the file is empty:
            while f.tell() < f.frames:
                chunk = f.read(f.samplerate)
                
                # Run the audio through our pedalboard:
                effected = board(chunk, f.samplerate, reset=False)
                
                # Write the output to our output file:
                o.write(effected)

    subprocess.call(['ffmpeg', '-i', fx_file, '-b:a', '256k', '-ar', '44100', mp3_file])

def save_to_file(text, filename, folder):
    os.makedirs(folder, exist_ok=True)
    out_file = os.path.join(folder, filename)
    with open(out_file, 'w') as f:
        f.write(text.__str__())

global_configs = {}


def read_config_from_file(config_file_path):
    config = {}
    try:
        with open(config_file_path, 'r') as file:
            for line in file:
                name, value = line.strip().split('=')
                value = value.strip() 
                name = name.strip() 
                if value.lower() == 'true':
                    config[name] = True
                elif value.lower() == 'false':
                    config[name] = False
                elif value.isdigit():
                    config[name] = int(value)
                else:
                    try:
                        config[name] = float(value)
                    except ValueError:
                        config[name] = value
    except FileNotFoundError:
        pass
    return config

################################################################################

def make_wav_from_prompt(sentence, sentence_file, directory): 


    RENDER_AUDIO_FILES = False


    TEST_GIBBERISH = True
    TEST_EVERY_SENTENCE_FOR_GIBBERISH = True
    TOTAL_ATTEMPTS_TO_MAKE_ONE_SENTENCE_WITHOUT_GIBBERSISH = 5
    GIBBERISH_DETECTION_THRESHOLD = 0.85 # Lower detects less gibberrish. 1.0 would contstantly detect gibberish and cause failure  [0.3 - 0.9]
    SPEAKER_SPEED = 0.9
    UPSAMPLE = False

    NOISE_REDUCTION_PROPORTION = 0.4
    VOICE_TO_USE = "coqui_voices\\twobob_master.wav"

    SIGNAL_GAIN_dB = -3.0
    SIGNAL_REVERB_ROOM_SIZE = 0.06
    SIGNAL_REVERB_DAMPING = 0.4
    SIGNAL_REVERB_WET_LEVEL = 0.15
    SIGNAL_REVERB_DRY_LEVEL = 0.7
    SIGNAL_REVERB_WIDTH = 0.9
    SIGNAL_REVERB_FREEZE = 0.0

    ACCENT_TO_USE = 'en' # 'en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'hu', 'ko', 'ja', 'hi'


    # Get device
    device = "cuda" if torch.cuda.is_available() else "cpu"

    from pedalboard import Pedalboard, Chorus, Reverb, PitchShift, Limiter, Gain
    from pedalboard.io import AudioFile

    from TTS.api import TTS
    #print(TTS().list_models())

    '''
            Args:
                model_name (str, optional): Model name to load. You can list models by ```tts.models```. Defaults to None.
                model_path (str, optional): Path to the model checkpoint. Defaults to None.
                config_path (str, optional): Path to the model config. Defaults to None.
                vocoder_path (str, optional): Path to the vocoder checkpoint. Defaults to None.
                vocoder_config_path (str, optional): Path to the vocoder config. Defaults to None.
                progress_bar (bool, optional): Whether to pring a progress bar while downloading a model. Defaults to True.
                DEPRECATED: gpu (bool, optional): Enable/disable GPU. Some models might be too slow on CPU. Defaults to False.
    '''
    #C:\Users\new\AppData\Local\tts\tts_models--multilingual--multi-dataset--xtts_v2\config.json
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", config_path="./tts_config.json", progress_bar=True).to(device)

    #story_files = find_story_files_without_mp3('story.txt')


    # If the configuration file exists, use it to override the global settings
    if directory in global_configs:
        config = global_configs[directory]
        RENDER_EVERY_SENTENCE = config.get('RENDER_EVERY_SENTENCE', RENDER_EVERY_SENTENCE) if config else True
        TEST_GIBBERISH = config.get('TEST_GIBBERISH', TEST_GIBBERISH) if config else True
        TEST_EVERY_SENTENCE_FOR_GIBBERISH = config.get('TEST_EVERY_SENTENCE_FOR_GIBBERISH', TEST_EVERY_SENTENCE_FOR_GIBBERISH) if config else True
        TOTAL_ATTEMPTS_TO_MAKE_ONE_SENTENCE_WITHOUT_GIBBERSISH = config.get('TOTAL_ATTEMPTS_TO_MAKE_ONE_SENTENCE_WITHOUT_GIBBERSISH', TOTAL_ATTEMPTS_TO_MAKE_ONE_SENTENCE_WITHOUT_GIBBERSISH) if config else 5
        GIBBERISH_DETECTION_THRESHOLD = config.get('GIBBERISH_DETECTION_THRESHOLD', GIBBERISH_DETECTION_THRESHOLD) if config else 0.85
        SPEAKER_SPEED = config.get('SPEAKER_SPEED', SPEAKER_SPEED) if config else 0.9
        UPSAMPLE = config.get('UPSAMPLE', UPSAMPLE) if config else True
        NOISE_REDUCTION_PROPORTION = config.get('NOISE_REDUCTION_PROPORTION', NOISE_REDUCTION_PROPORTION) if config else 0.4
        VOICE_TO_USE = config.get('VOICE_TO_USE', VOICE_TO_USE) if config else "coqui_voices\\twobob_master.wav"
        SIGNAL_GAIN_dB = config.get('SIGNAL_GAIN_dB', SIGNAL_GAIN_dB) if config else 3.0
        SIGNAL_REVERB_ROOM_SIZE = config.get('SIGNAL_REVERB_ROOM_SIZE', SIGNAL_REVERB_ROOM_SIZE) if config else 0.06
        SIGNAL_REVERB_DAMPING = config.get('SIGNAL_REVERB_DAMPING', SIGNAL_REVERB_DAMPING) if config else 0.4
        SIGNAL_REVERB_WET_LEVEL = config.get('SIGNAL_REVERB_WET_LEVEL', SIGNAL_REVERB_WET_LEVEL) if config else 0.15
        SIGNAL_REVERB_DRY_LEVEL = config.get('SIGNAL_REVERB_DRY_LEVEL', SIGNAL_REVERB_DRY_LEVEL) if config else 0.7
        SIGNAL_REVERB_WIDTH = config.get('SIGNAL_REVERB_WIDTH', SIGNAL_REVERB_WIDTH) if config else 0.9
        SIGNAL_REVERB_FREEZE = config.get('SIGNAL_REVERB_FREEZE', SIGNAL_REVERB_FREEZE) if config else 0.0
        ACCENT_TO_USE = config.get('ACCENT_TO_USE', ACCENT_TO_USE) if config else 'en' 
        ACCENT_TO_USE = ACCENT_TO_USE.lower()

        # Make a Pedalboard object, containing multiple audio plugins:
    board = Pedalboard([#PitchShift(semitones = -1.0), 
                            Gain(gain_db = SIGNAL_GAIN_dB * 0.5),
                            Reverb(room_size = SIGNAL_REVERB_ROOM_SIZE, damping = SIGNAL_REVERB_DAMPING, wet_level = SIGNAL_REVERB_WET_LEVEL, dry_level = SIGNAL_REVERB_DRY_LEVEL, width = SIGNAL_REVERB_WIDTH, freeze_mode = SIGNAL_REVERB_FREEZE),
                            Gain(gain_db = SIGNAL_GAIN_dB * 0.5)
                            ])     


    ''' def tts_to_file(
            self,
            text: str,
            speaker: str = None,
            language: str = None,
            speaker_wav: str = None,
            emotion: str = None,
            speed: float = 1.0,
            pipe_out=None,
            file_path: str = "output.wav",
            split_sentences: bool = True,
            **kwargs,
        ):
    '''


    sentence_file  = os.path.basename(sentence_file)
    pathed_wav_filename = os.path.join(directory, sentence_file)
    

    if TEST_EVERY_SENTENCE_FOR_GIBBERISH and TEST_GIBBERISH:
        # assume gibberish to force a recreation attempt in the event of found gibberish.
        total_gibberish = 1 
        attempts = 0                               
        while total_gibberish > 0 and attempts < TOTAL_ATTEMPTS_TO_MAKE_ONE_SENTENCE_WITHOUT_GIBBERSISH:
            #make the file
            tts.tts_to_file(text=sentence, 
                            speed=SPEAKER_SPEED, 
                            speaker_wav=VOICE_TO_USE, 
                            split_sentences=False, 
                            language=ACCENT_TO_USE, 
                            file_path=pathed_wav_filename)                                           
            #test it for validity (confidence that it is "a known language to whisper")
            total_gibberish = gibberish_extractor.process_audio(pathed_wav_filename, GIBBERISH_DETECTION_THRESHOLD)

    else:
        tts.tts_to_file(text=sentence, 
                        speed=SPEAKER_SPEED, 
                        speaker_wav=VOICE_TO_USE, 
                        split_sentences=False, 
                        language=ACCENT_TO_USE, 
                        file_path=pathed_wav_filename)
        
    if UPSAMPLE:

        input_file = pathed_wav_filename
        checkpoint = ".\\nuwave2\\nuwave2_02_16_13_epoch=629.ckpt"
        sample_rate = 24000
        print(f"input_file = {input_file}")
        new_file = inference.infer(checkpoint=checkpoint,wav_file=pathed_wav_filename, sample_rate=sample_rate, steps=8, gt=False, device=device)
        print(f"new_file is {new_file}")
        #swap result to old output                                 
        edited_file_path = sentence_file.rsplit(".", 1)[0] + "_edited.wav"
        os.replace( r"./nuwave2/test_sample/result/result.wav", os.path.join(directory,edited_file_path))
        clean_and_backup_audio(os.path.join(directory,edited_file_path), NOISE_REDUCTION_PROPORTION)   

        if RENDER_AUDIO_FILES:            
            # Concatenate all rendered sentences into a single audio file
            concatenated_audio = AudioSegment.empty()
            for i in range(len(split_sentences)):
                sentence_file = os.path.join(rendered_folder, f"sentence_{i}_edited.wav") if TEST_GIBBERISH else os.path.join(rendered_folder, f"sentence_{i}.wav")
                try:
                    sentence_audio = AudioSegment.from_wav(sentence_file)
                except:
                    deletion_audio  = os.path.join(rendered_folder, f"sentence_{i}.wav")    
                    if os.path.exists(deletion_audio):
                        os.remove(deletion_audio)
                        print("seed wav deleted successfully.")
                    else:
                        print("Seed wav does not exist.")

                concatenated_audio += sentence_audio

            # Save the concatenated audio to the original filename
            concatenated_audio.export(sentence_file, format="wav")

            convert_wav_to_mp3(sentence_file, fx_filename, mp3_filename, directory)

if __name__ == "__main__":


    prompt = sys.argv[1]
    file_name = sys.argv[2]
    directory = sys.argv[3]
    make_wav_from_prompt(prompt, file_name, directory)                
