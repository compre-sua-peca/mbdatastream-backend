import os
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad
# from numpy import pad
import hashlib

##Alteração de lib "pad" do numpy para Crypto
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

    def generate_hash(self, name: str) -> str:
        """
        Encrypts the brand name deterministically using AES-256-CBC.
        Returns the hash in the format: "brand_name-encrypted_hex"
        """
        treated_name: str = name.replace(" ", "")
        
        try:
            iv = self.generate_iv(treated_name)
            cipher = AES.new(self.ENCRYPTION_BRAND_KEY, AES.MODE_CBC, iv)
            
            padded_data = pad(name.encode(), AES.block_size)
            
            encrypted_bytes = cipher.encrypt(padded_data)
            encrypted_hex = encrypted_bytes.hex()
            
            return f"{treated_name}-{encrypted_hex}"
        except Exception as e:
            print(f"Encryption error for {name}: {str(e)}. Using fallback hash")
            hash_value = hashlib.sha256(name.encode()).hexdigest()[:16]
            
            return f"{treated_name}-{hash_value}"
            
            