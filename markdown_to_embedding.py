from pathlib import Path
from semantic_text_splitter import MarkdownSplitter
from tqdm import tqdm
import numpy as np
from llms import Nomic

client = Nomic()


def get_chunks_from_markdown(file_path: Path, chunk_size: int = 2048) -> list:
    """
    Splits a markdown file into chunks of specified size.

    Args:
        file_path (Path): Path to the markdown file.
        chunk_size (int): Size of each chunk in characters.

    Returns:
        list: List of text chunks.
    """
    splitter = MarkdownSplitter(chunk_size)
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    return splitter.chunks(text)


if __name__ == "__main__":
    files = [*Path("tds_pages_md").glob("*.md"), *Path("discourse_md").glob("*.md")]
    all_chunks = []
    all_embeddings = []
    total_chunks = 0
    file_chunks = {}
    for file_path in files:
        chunks = get_chunks_from_markdown(file_path)
        file_chunks[file_path] = chunks
        total_chunks += len(chunks)
    
    with tqdm(total=total_chunks, desc="Processing files") as pbar:
        for file_path, chunks in file_chunks.items():
            for chunk in chunks:
                try:
                    embedding = client.get_embedding(chunk)
                    all_chunks.append(chunk)
                    all_embeddings.append(embedding)
                    pbar.update(1)
                except Exception as e:
                    print(f"Error processing chunk from {file_path}: {e}")
                    pbar.update(1)
                    continue

    np.savez_compressed("tds_course.npz", chunks=all_chunks, embeddings=all_embeddings)
    # Example usage
    # file_path = Path("tds_pages_md/CORS.md")  # Replace with your markdown file path

    # chunks = get_chunks_from_markdown(file_path)

    # # Print the number of chunks and their lengths
    # print(f"Number of chunks: {len(chunks)}")
    # for i, chunk in enumerate(chunks):
    #     print(f"Chunk {i+1} length: {len(chunk)} characters")