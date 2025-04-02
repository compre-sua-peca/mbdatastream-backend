import os
from Crypto.Cipher import AES
from Crypto.Hash import SHA256

class HashGenerator:
    def __init__(self):
        # Get the secret for brand encryption from an environment variable
        self.SECRET_BRAND = os.environ.get("HASH_SECRET_KEY")
        # Create the encryption key by hashing the secret using SHA-256
        self.ENCRYPTION_BRAND_KEY = SHA256.new(self.SECRET_BRAND.encode()).digest()
        self.IV_LENGTH = 16

    def generate_iv(self, value: str) -> bytes:
        """
        Generate a deterministic IV by hashing the value and taking the first IV_LENGTH bytes.
        """
        hash_obj = SHA256.new(value.encode())
        return hash_obj.digest()[:self.IV_LENGTH]

    def _pad(self, s: str) -> bytes:
        """
        Apply PKCS7 padding to ensure the data is a multiple of AES block size.
        """
        bs = AES.block_size
        pad_len = bs - (len(s) % bs)
        padding = chr(pad_len) * pad_len
        return (s + padding).encode()

    def generate_hash(self, name: str) -> str:
        """
        Encrypts the brand name deterministically using AES-256-CBC.
        Returns the hash in the format: "brand_name-encrypted_hex"
        """
        iv = self.generate_iv(name)
        cipher = AES.new(self.ENCRYPTION_BRAND_KEY, AES.MODE_CBC, iv)
        padded_brand_name = self._pad(name)
        encrypted_bytes = cipher.encrypt(padded_brand_name)
        encrypted_hex = encrypted_bytes.hex()
        
        return f"{name}-{encrypted_hex}"
