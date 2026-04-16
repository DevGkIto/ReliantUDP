import string
import random

FILENAME = "test.txt"
SIZE_KB = 100  # Set your target here in KB

def generate_file(filename, size_kb):
    size_bytes = int(size_kb * 1024)
    chars = string.ascii_letters + string.digits + " \n"
    
    print(f"[*] Generating {size_kb}KB test file ({size_bytes} bytes)...")
    
    with open(filename, 'w') as f:
        # We generate the whole chunk at once since 100KB is tiny for RAM
        content = ''.join(random.choices(chars, k=size_bytes))
        f.write(content)
            
    print(f"[+] Done. Created {filename}")

if __name__ == "__main__":
    generate_file(FILENAME, SIZE_KB)