import tiktoken

enc = tiktoken.get_encoding("o200k_base")

print(enc.encode("Hello, world!"))
