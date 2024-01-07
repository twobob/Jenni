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

import nltk
from tqdm import tqdm
import os
import re
import os
import time
import torch
import sys
import chardet


def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result

def contains_substring(main_string, substring):
    return substring in main_string  

def save_to_file(text, filename, folder):
    os.makedirs(folder, exist_ok=True)
    out_file = os.path.join(folder, filename)
    with open(out_file, 'w') as f:
        f.write(text.__str__())

def has_sentence_files(directory):
    txt_file_pattern = re.compile(r'sentence_\d+\.txt$')
    rendered_sentences_dir = os.path.join(directory, "rendered_sentences")
    if os.path.exists(rendered_sentences_dir):
        txt_files = [f for f in os.listdir(rendered_sentences_dir) if txt_file_pattern.match(f)]
        return len(txt_files) > 0
    else:
        return False

def find_all_story_files_without_sentence_files(filename='story.txt', directory='.'):
    all_story_files = {}

    for root, dirs, files in os.walk(directory):
        if filename in files and not has_sentence_files(root):
            all_story_files[os.path.join(root, filename)] = root

    return all_story_files

def find_all_story_files(filename='story.txt', directory='.'):
    all_story_files = {}

    # Walk through each directory in the current directory
    for root, dirs, files in os.walk(directory):
        # If 'story.txt' is in the files and 'story.mp3' is not
        if filename in files:
            # Add the file and its directory to the dictionary
            all_story_files[os.path.join(root, filename)] = root
    return all_story_files

def remove_multiple_backslashes(input_str):
    # Convert the string to ASCII tokens
    ascii_tokens = [ord(char) for char in input_str]

    backslash_char = 92
    # Process the ASCII tokens to replace multiple consecutive chr(92) with a single one
    processed_tokens = []
    prev_token = None
    for token in ascii_tokens:
        if token == backslash_char and prev_token == backslash_char:
            continue
        processed_tokens.append(token)
        prev_token = token

    # Convert the processed ASCII tokens back to a string
    return ''.join(chr(token) for token in processed_tokens)

def replace_with_case(word, replacement, text):
    def replacer(match):
        if match.group().isupper():
            return replacement.upper()
        elif match.group().islower():
            return replacement.lower()
        elif match.group()[0].isupper():
            return replacement.capitalize()
        else:
            return replacement

    word_pattern = r'\b' + word + r'\b'
    return re.sub(word_pattern, replacer, text, flags=re.IGNORECASE)

def tidy_up_sentence_formatting(sentence):
    for test_str in ["\\n"]:
        if contains_substring(sentence, test_str):                          
            sentence = sentence.replace(test_str, "")

    for test_str in ["\"', ","\", ", "', "]:
        if sentence.startswith(test_str):
            sentence = sentence.replace(test_str, "")

    for test_str in ["\"\""]:
        if contains_substring(sentence, test_str):                          
            sentence = sentence.replace(test_str, "\"")      

    # Replace n backslashes with one backslash     
    ## Not required, further investigation showed one chr(92) despite the UI showing multiple \\\ \\       
    # sentence = remove_multiple_backslashes(sentence)
                                    
    #engine cant say this word correctly very well.
    for test_str in ["chaotic,","chaotic ","chaotic!","chaotic?","chaotic.","chaotic\""]:
        if contains_substring(sentence, test_str):                          
            sentence = sentence.replace("chaotic", f"crazy")

    #engine cant say this word correctly very well.
    # Replacing "inhale" and "exhale" considering case sensitivity
    sentence = replace_with_case("Inhale", "Breathe in", sentence)
    sentence = replace_with_case("Exhale", "Breathe out", sentence)
    sentence = replace_with_case("inhale", "breathe in", sentence)
    sentence = replace_with_case("exhale", "breathe out", sentence)    
    sentence = replace_with_case("sinuses", "airways", sentence)
    sentence = replace_with_case("widening", "wide", sentence)

    #engine cant say this word correctly very well.
    for test_str in ["Genuine", "genuine,","genuine ","genuine!","genuine?","genuine.","genuine\""]:
        if contains_substring(sentence, test_str):                          
            sentence = sentence.replace("genuine", f"real") 
            sentence = sentence.replace("Genuine", "Real" )               
    
    return sentence



def story_split(passed_directory ='.'):

    story_files = find_all_story_files('story.txt', passed_directory)

    for file, directory in tqdm(story_files.items(), desc="Processing files", ncols=70):
        print(f"File: {file}, Directory: {directory}")

        prefix = os.path.basename(directory)
        
        #if not any(f.endswith('_fx.wav') for f in os.listdir(directory)) or RENDER_TEXT_FILES:

        encoding = detect_encoding(file)

        if encoding["encoding"] == 'Johab':
            encoding["encoding"] = 'Windows-1252'

        print(f"encoding detected as {encoding}")

        with open(file=file, mode="r", encoding=encoding["encoding"]) as chapter_text_file:

            text = chapter_text_file.read()

            sentences = nltk.sent_tokenize(text)

            discard_starts = [
                "### Instruction:",
                "### User",
                "###User",
                "Place:",
                "Time:",
                "### Assistant",
                "[PROMPT]",
                "[End scene.]",
                "The story value",
                "Story value charge:",
                "\nThis scene",
                "A/N: This scene",
                "Story value:",
                "\nThe End",
                "Outcome:",
                "Mood:",
                "The End."
            ]

            filtered_sentences = [sentence for sentence in sentences if not any(sentence.startswith(s) for s in discard_starts)]
            if len(sentences) > len(filtered_sentences):
                print(f"{ len(sentences) - len(filtered_sentences) } sentences filtered")

            # Split sentences that are longer than 250 characters
            split_sentences = []
            severed_sentences = 0
            for sentence in filtered_sentences:
                while len(sentence) > 250:
                    # Find the last period or comma in the first 250 characters
                    match = re.search('[.,]', sentence[:250][::-1])
                    severed_sentences = severed_sentences + 1
                    if match:
                        split_point = 250 - match.start()
                        split_sentences.append(sentence[:split_point])
                        sentence = sentence[split_point:]
                    else:
                        # If no period or comma is found, split at the 250th character
                        split_sentences.append(sentence[:250])
                        sentence = sentence[250:]
                split_sentences.append(sentence)
            
            if severed_sentences > 0:
                print (f'Split {severed_sentences} sentences to fit the en 250 char barrier')

            chapter_text = '\n'.join(split_sentences)

            # Create a subfolder for the rendered sentences
            rendered_folder = os.path.join(os.path.dirname(chapter_text_file.name), "rendered_sentences")
            os.makedirs(rendered_folder, exist_ok=True)

            # Render each sentence and save it to the subfolder
            for i, sentence in enumerate(tqdm(split_sentences, desc="Processing sentence", ncols=70)):

                text_filename = os.path.join(rendered_folder, f"sentence_{i}.txt")
                if not os.path.exists(text_filename):
                    sentence = tidy_up_sentence_formatting(sentence)
                    with open(text_filename, 'w') as file:
                        content = file.write(sentence)