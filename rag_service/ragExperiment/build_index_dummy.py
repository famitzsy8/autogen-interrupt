import json, re, pathlib, faiss, numpy as np
import os, faulthandler, torch
from sentence_transformers import SentenceTransformer
import tiktoken
import torch.multiprocessing

# Force single-threaded execution for reproducibility and to avoid OpenMP conflicts
faulthandler.enable()
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.set_num_threads(1)


# Simplified configuration for demo
JSON_PATH = "./congressMCP/analysis/ragExperiment/committee_meetings_116_senate_50.json"  # smaller dataset
INDEX_DIR = pathlib.Path("index_demo")
EMBED_MODEL = "all-MiniLM-L6-v2"
TOKENS_PER_CHUNK = 256  # smaller chunks for demonstration
BATCH = 4  # smaller batch size to see process clearly

print("\n🔧 Initializing RAG components...")
print(f"📁 Reading from: {JSON_PATH}")
print(f"💾 Saving index to: {INDEX_DIR}")
print(f"🤖 Using embedding model: {EMBED_MODEL}")
print(f"📏 Chunk size: {TOKENS_PER_CHUNK} tokens")
print(f"📦 Batch size: {BATCH} chunks\n")

# Initialize components
enc = tiktoken.get_encoding("cl100k_base")
print("✓ Initialized cl100k_base tokenizer")

model = SentenceTransformer(EMBED_MODEL, device="cpu")
dim = model.get_sentence_embedding_dimension()
print(f"✓ Initialized sentence transformer (embedding dim: {dim})")

index = faiss.IndexFlatIP(dim)
print("✓ Initialized FAISS index for similarity search\n")

meta = []  # store metadata about chunks
tok_re = re.compile(r"\w+|\S")  # fallback tokenization

def chunk(text, show_example=False):
    """Split text into chunks of approximately TOKENS_PER_CHUNK tokens."""
    try:
        # Convert text to tokens and back to ensure consistent chunking
        toks = enc.encode(text)
        if show_example:
            print(f"🔍 Example tokenization:")
            print(f"   Original text length: {len(text)} characters")
            print(f"   Number of tokens: {len(toks)}")
            print(f"   First 5 tokens: {toks[:5]}")
            print(f"   These decode to: {enc.decode(toks[:5])}\n")
        
        for i in range(0, len(toks), TOKENS_PER_CHUNK):
            chunk = enc.decode(toks[i:i+TOKENS_PER_CHUNK])
            if show_example and i == 0:
                print(f"📄 First chunk ({len(toks[i:i+TOKENS_PER_CHUNK])} tokens):")
                print(f"   {chunk[:100]}...\n")
            yield chunk
    except Exception as e:
        print(f"⚠️ Tokenization failed: {e}. Using fallback method.")
        words = tok_re.findall(text)
        for i in range(0, len(words), TOKENS_PER_CHUNK):
            yield " ".join(words[i:i+TOKENS_PER_CHUNK])

def process_meeting(meeting_data):
    """Process a single meeting document."""
    congress = meeting_data.get('congress', 'unknown')
    chamber = meeting_data.get('chamber', 'unknown')
    meet_id = meeting_data.get('meeting_id', 'unknown')
    text = meeting_data.get('text', '')
    
    print(f"\n📑 Processing meeting: {congress}/{chamber}/{meet_id}")
    print(f"   Original text length: {len(text)} characters")
    return congress, chamber, meet_id, text

def main():
    # Main processing loop
    print("🚀 Starting document processing...")
    batch_txt, batch_ids = [], []
    total_chunks = 0

    # Read and process the smaller JSON file
    with open(JSON_PATH, 'r') as f:
        meetings = json.load(f)
        congress, chamber = "116", "senate"
        print(f"📚 Loaded {len(meetings)} meetings\n")
        for meeting_id, meeting_text in meetings[congress][chamber].items():

            print(meeting_id)
            
            # Show tokenization example for first document only
            show_example = (total_chunks == 0)
            
            for i, part in enumerate(chunk(meeting_text, show_example)):
                batch_txt.append(part)
                batch_ids.append((congress, chamber, meeting_id, i))
                total_chunks += 1
                
                if len(batch_txt) == BATCH:
                    print(f"\n💫 Processing batch of {BATCH} chunks...")
                    embs = model.encode(batch_txt, normalize_embeddings=True)
                    print(embs[:15])
                    print(f"   Generated embeddings shape: {embs.shape}")
                    
                    index.add(np.asarray(embs, "float32"))
                    meta.extend(batch_ids)
                    print(f"   Added to FAISS index (total vectors: {index.ntotal})")
                    
                    batch_txt, batch_ids = [], []

    # Process any remaining chunks
    if batch_txt:
        print(f"\n💫 Processing final batch of {len(batch_txt)} chunks...")
        embs = model.encode(batch_txt, normalize_embeddings=True)
        print(f"   Generated embeddings shape: {embs.shape}")
        
        index.add(np.asarray(embs, "float32"))
        meta.extend(batch_ids)
        print(f"   Added to FAISS index (total vectors: {index.ntotal})")

    # Save the results
    INDEX_DIR.mkdir(exist_ok=True)
    faiss.write_index(index, str(INDEX_DIR / "faiss.bin"))
    print(f"\n💾 Saved FAISS index to {INDEX_DIR}/faiss.bin")

    with open(INDEX_DIR / "meta.jsonl", "w") as f:
        for m in meta:
            json.dump(m, f)
            f.write("\n")
    print(f"📝 Saved metadata to {INDEX_DIR}/meta.jsonl")

    print(f"\n✨ Index built successfully!")
    print(f"   Total passages indexed: {len(meta)}")
    print(f"   Total vectors in FAISS: {index.ntotal}")
    print(f"   Vector dimension: {dim}")


if __name__ == "__main__":
    torch.multiprocessing.set_start_method('spawn', force=True)
    main()