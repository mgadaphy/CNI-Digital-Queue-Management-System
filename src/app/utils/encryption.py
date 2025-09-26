from cryptography.fernet import Fernet
from flask import current_app
import base64
import os

class DataEncryption:
    """Utility class for encrypting and decrypting sensitive data"""
    
    def __init__(self):
        self._cipher = None
    
    @property
    def cipher(self):
        if self._cipher is None:
            key = current_app.config.get('ENCRYPTION_KEY')
            if not key:
                # Generate a new key if none exists (for development)
                key = Fernet.generate_key()
                current_app.logger.warning("No encryption key found, using generated key")
            
            if isinstance(key, str):
                key = key.encode()
            
            self._cipher = Fernet(key)
        return self._cipher
    
    def encrypt(self, data):
        """Encrypt sensitive data"""
        if data is None:
            return None
        
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.cipher.encrypt(data)
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data):
        """Decrypt sensitive data"""
        if encrypted_data is None:
            return None
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            current_app.logger.error(f"Decryption failed: {e}")
            return None
    
    def encrypt_phone(self, phone_number):
        """Encrypt phone number with additional formatting"""
        if not phone_number:
            return None
        
        # Remove any formatting and encrypt
        clean_phone = ''.join(filter(str.isdigit, phone_number))
        return self.encrypt(clean_phone)
    
    def decrypt_phone(self, encrypted_phone):
        """Decrypt and format phone number"""
        if not encrypted_phone:
            return None
        
        decrypted = self.decrypt(encrypted_phone)
        if decrypted and len(decrypted) >= 10:
            # Format as (XXX) XXX-XXXX for display
            return f"({decrypted[:3]}) {decrypted[3:6]}-{decrypted[6:]}"
        return decrypted

# Global encryption instance
encryption = DataEncryption()