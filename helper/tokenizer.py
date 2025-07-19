import tiktoken
import sys
import os
import shutil
def getNumTokens(file_path):
    """
    Given a file with structure {congress: {chamber: {eventid: text, ...}, ...}, ...},
    returns the total number of tokens in all meeting texts.
    Uses tiktoken if available, otherwise falls back to word count.
    """
    with open(file_path, 'r') as f:
        data = f.read()
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(data))
    except ImportError:
        # Fallback: count words as a rough proxy
        return len(data.split())

def splitIntoChunks(file_name, chunk_size=32000, overlap_size=500):
    directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "texts")
    file_path = os.path.join(directory, file_name)
    with open(file_path, 'r') as f:
        text = f.read()
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    if overlap_size >= chunk_size:
        raise ValueError("Overlap size must be smaller than chunk size.")

    chunks = []
    step_size = chunk_size - overlap_size
    for i in range(0, len(tokens), step_size):
        chunk = tokens[i:i + chunk_size]
        if chunk:
            chunks.append(enc.decode(chunk))

    _exportToTextChunks(chunks, file_name)
    print(f"Split {file_name} into {len(chunks)} chunks")
    print(f"Total tokens: {len(tokens)}")
    avg_tokens = sum(len(enc.encode(c)) for c in chunks) / len(chunks) if chunks else 0
    print(f"Average tokens per chunk: {avg_tokens:.2f}")
    print(f"Chunk size (max): {chunk_size}, Overlap: {overlap_size} tokens")

def _exportToTextChunks(chunks, file_name):
    directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chunks", file_name[:-4]) # remove .txt
    os.makedirs(directory, exist_ok=True)
    __removeFilesFromDirectory(directory)
    for i, chunk in enumerate(chunks):
        file_path = os.path.join(directory, f"{file_name[:-4]}_{i}.txt")
        with open(file_path, 'w') as f:
            f.write(chunk)
            f.close()

def __removeFilesFromDirectory(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)  # Remove file or link
        elif os.path.isdir(file_path):
            import shutil
            shutil.rmtree(file_path)

file_name = sys.argv[1]
splitIntoChunks(file_name, chunk_size=50000, overlap_size=1500)