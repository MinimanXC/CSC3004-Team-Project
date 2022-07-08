""" Script to take in multiple arguments and hash in SHA256 """
from hashlib import sha256

# Function to combine multiple strings and output a single hash
def calculateHash(*args) -> str:
    hashingText = ''
    h = sha256()

    for arg in args:
        hashingText += str(arg)

    h.update(hashingText.encode('utf-8'))
    return h.hexdigest()
