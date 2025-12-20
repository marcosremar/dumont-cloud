import hashlib
password = "dumont123"
hash_obj = hashlib.sha256(password.encode())
print(hash_obj.hexdigest())
