# with open("disk.img", "wb") as f:
#     f.write(b"\x00" * 10 * 1024 * 1024)


import os

# Create the fake FAT32 image
size = 1024 * 1024  # 1 MB

boot_sector_size = 512
fat_size = 4096
root_dir_size = 16384

data_region_offset = boot_sector_size + fat_size * 2 + root_dir_size

with open("fake_fat32.img", "wb") as f:
    # Boot sector placeholder (512 bytes)
    f.write(b'\xEB\x3C\x90' + b'FAKEFAT ' + b'\x00' * (boot_sector_size - 11))

    # FAT #1
    f.write(b'\xF8\xFF\xFF\x0F' + b'\x00' * (fat_size - 4))

    # FAT #2
    f.write(b'\xF8\xFF\xFF\x0F' + b'\x00' * (fat_size - 4))

    # Root directory table
    f.write(b'\x00' * root_dir_size)

    # Data region padding (we fill it later)
    remaining = size - f.tell()
    f.write(b'\x00' * remaining)

print("Disk image created.")


# -----------------------------
# Now insert a jpg file manually
# -----------------------------

jpg_path = "cat.jpg"   # <-- replace with your jpg
with open(jpg_path, "rb") as p:
    jpg_bytes = p.read()

jpg_size = len(jpg_bytes)

# Insert jpg at start of data region
with open("fake_fat32.img", "r+b") as img:
    img.seek(data_region_offset)
    img.write(jpg_bytes)

print(f"Inserted {jpg_size} bytes of jpg data at offset {data_region_offset}.")
