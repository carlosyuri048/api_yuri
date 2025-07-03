import os
import base64

def generate_symmetric_key(length_bytes):
    """
    Gera uma chave simétrica criptograficamente segura.

    Args:
        length_bytes (int): O comprimento da chave em bytes.
                            Recomendado: 32 bytes (256 bits) para HS256,
                            48 bytes (384 bits) para HS384,
                            64 bytes (512 bits) para HS512.

    Returns:
        str: A chave gerada codificada em Base64 para facilitar o uso.
    """
    key = os.urandom(length_bytes)
    return base64.urlsafe_b64encode(key).decode('utf-8')

# Exemplo para HS256 (32 bytes = 256 bits)
jwt_secret_key_hs256 = generate_symmetric_key(32)
print(f"Chave HS256: {jwt_secret_key_hs256}")

# Exemplo para HS512 (64 bytes = 512 bits)
jwt_secret_key_hs512 = generate_symmetric_key(64)
print(f"Chave HS512: {jwt_secret_key_hs512}")