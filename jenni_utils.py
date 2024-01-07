import re

def find_matching_index(list1, list2, index):
    """
    Finds the index of a file in list2 that matches the pattern extracted from a file in list1 at the given index.
    
    :param list1: The list containing the original file.
    :param list2: The list to search for a matching file.
    :param index: The index in list1 of the file to find in list2.
    :return: The index of the matching file in list2, or -1 if no match is found.
    """
    if index >= len(list1):
        return -1  # Index is out of range for list1

    # Extract the sentence pattern from the file at the given index in list1
    pattern = re.search(r'sentence_\d+', list1[index])
    if not pattern:
        return -1  # Pattern not found in the file from list1

    sentence_pattern = pattern.group()

    # Search for a file in list2 that contains the extracted pattern
    for i, file in enumerate(list2):
        if sentence_pattern in file:
            return i  # Found a match at index i in list2

    return -1  # No match found in list2

