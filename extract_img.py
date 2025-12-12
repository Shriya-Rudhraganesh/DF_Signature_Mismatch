from PIL import Image
from io import BytesIO

# Load the raw disk image
with open("fake_fat32.img", "rb") as f:
    data = f.read()

# JPEG start and end signatures
start_sig = b"\xFF\xD8\xFF"
end_sig   = b"\xFF\xD9"

# Find start of JPEG
start = data.find(start_sig)
if start == -1:
    raise ValueError("No JPEG start signature found.")

# Find end of JPEG AFTER the start
end = data.find(end_sig, start)
if end == -1:
    raise ValueError("No JPEG end signature found.")

# Extract the entire JPEG (end + 2 bytes to include 0xFFD9)
jpg_bytes = data[start:end+2]

# Write recovered file
with open("recovered.jpg", "wb") as out:
    out.write(jpg_bytes)

print("Recovered JPG from bytes", start, "to", end+2)

# Render it (display)
img = Image.open(BytesIO(jpg_bytes))
img.show()  # This opens the system image viewer
