import hashlib


def create_checksum(file_path: str):
    hash = hashlib.md5()
    block_size = 128 * hash.block_size
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            hash.update(chunk)
    return hash.digest()
