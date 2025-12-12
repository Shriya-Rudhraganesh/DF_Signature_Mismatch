import struct
import os

IMAGE = "fake_fat32.img"

CLUSTER_SIZE = 4096
BOOT_SIZE = 512
FAT_SIZE = 4096
ROOT_DIR_SIZE = 16384
DATA_OFFSET = BOOT_SIZE + FAT_SIZE*2 + ROOT_DIR_SIZE


# ----------------------------
# SIGNATURE DEFINITIONS
# ----------------------------

JPEG_SIG = b"\xFF\xD8\xFF"

MP4_SIG_1 = b"\x00\x00\x00\x18\x66\x74\x79\x70"
MP4_SIG_2 = b"\x00\x00\x00\x14\x66\x74\x79\x70\x69\x73\x6F\x6D"

def is_jpeg(header):
    return header.startswith(JPEG_SIG)

def is_mp4(header):
    return header.startswith(MP4_SIG_1) or header.startswith(MP4_SIG_2)


# ----------------------------
# READ DIRECTORY ENTRIES
# ----------------------------

def scan_entire_image_for_jpeg():
    """Scan the entire data area for embedded JPEG signatures and report their offsets."""
    found = []
    with open(IMAGE, "rb") as img:
        img.seek(DATA_OFFSET)
        cluster_num = 2
        while True:
            data = img.read(CLUSTER_SIZE)
            if not data:
                break
            idx = data.find(JPEG_SIG)
            if idx != -1:
                offset = img.tell() - len(data) + idx
                print(f"JPEG signature found at offset {offset} (cluster {cluster_num}, cluster offset {idx})")
                found.append((cluster_num, offset))
            cluster_num += 1
    if not found:
        print("No embedded JPEG signatures found in image.")
    return found

def list_entries():
    entries = []

    root_offset = BOOT_SIZE + FAT_SIZE*2

    with open(IMAGE, "rb") as img:
        img.seek(root_offset)
        root = img.read(ROOT_DIR_SIZE)

        for i in range(0, len(root), 32):
            entry = root[i:i+32]

            if entry[0] == 0x00:
                break  # no more entries

            deleted = (entry[0] == 0xE5)

            # fix: short name begins at offset 0 (not 1)
            name = entry[0:8].decode("ascii", "ignore").strip()
            ext  = entry[8:11].decode("ascii", "ignore").strip()

            if name == "":
                continue  # empty or malformed entry

            attr = entry[11]
            # fix: handle FAT32 first-cluster high word (at 20:22) + low word (26:28)
            high = struct.unpack("<H", entry[20:22])[0]
            low  = struct.unpack("<H", entry[26:28])[0]
            first_cluster = (high << 16) | low
            # for FAT16 images high will be 0 and this yields the low value as before
            size = struct.unpack("<I", entry[28:32])[0]

            entries.append({
                "deleted": deleted,
                "name": name,
                "ext": ext,
                "cluster": first_cluster,
                "size": size
            })

    return entries


# ----------------------------
# READ FILE HEADER
# ----------------------------

def read_first_bytes(cluster, length):
    with open(IMAGE, "rb") as img:
        cluster_offset = DATA_OFFSET + (cluster - 2) * CLUSTER_SIZE
        img.seek(cluster_offset)
        return img.read(length)


def extract_jpeg_from_cluster(cluster, out_path):
    """Scan the image starting at the given cluster for a JPEG end marker and write the recovered jpeg to out_path.

    Returns True on success, False otherwise.
    """
    start_sig = JPEG_SIG
    end_sig = b"\xFF\xD9"

    cluster_offset = DATA_OFFSET + (cluster - 2) * CLUSTER_SIZE

    with open(IMAGE, "rb") as img:
        img.seek(cluster_offset)

        # We'll read in chunks and search for the end signature.
        buffer = b""
        chunk_size = 4096

        # First, ensure the start signature exists at or after cluster_offset.
        # Read until we find the start signature or we reach EOF.
        found_start = False
        while True:
            chunk = img.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            idx = buffer.find(start_sig)
            if idx != -1:
                # trim buffer to start at JPEG start
                buffer = buffer[idx:]
                found_start = True
                break

            # keep last len(start_sig)-1 bytes in case signature splits across reads
            if len(buffer) > len(start_sig):
                buffer = buffer[-(len(start_sig)-1):]

        if not found_start:
            return False

        # Now read until we find the end signature
        while True:
            idx_end = buffer.find(end_sig)
            if idx_end != -1:
                # include end_sig (2 bytes)
                jpg_data = buffer[:idx_end+2]
                with open(out_path, "wb") as out:
                    out.write(jpg_data)
                return True

            chunk = img.read(chunk_size)
            if not chunk:
                # reached EOF without finding end
                return False
            buffer += chunk
            # prevent buffer from growing unboundedly; keep reasonable tail
            if len(buffer) > 10 * 1024 * 1024:  # 10 MB
                # keep last 1MB in case marker crosses boundary
                buffer = buffer[-(1 * 1024 * 1024):]



# ----------------------------
# ANALYSIS + MISLABEL DETECTION
# ----------------------------

# add cluster scan helpers
def scan_cluster_data(cluster, max_bytes=CLUSTER_SIZE * 4):
    """Read up to max_bytes starting at the given cluster (cap multiple clusters)."""
    with open(IMAGE, "rb") as img:
        cluster_offset = DATA_OFFSET + (cluster - 2) * CLUSTER_SIZE
        img.seek(cluster_offset)
        return img.read(max_bytes)

def cluster_contains_jpeg(cluster):
    data = scan_cluster_data(cluster)
    return JPEG_SIG in data

def cluster_contains_mp4(cluster):
    data = scan_cluster_data(cluster)
    return (MP4_SIG_1 in data) or (MP4_SIG_2 in data)

def analyze_files():
    entries = list_entries()

    # Collections for summary reporting
    deleted_files = []
    mp4_wrong_ext = []
    jpeg_correct_ext = []

    for e in entries:
        name = e["name"]
        ext = e["ext"].upper()
        cluster = e["cluster"]
        size = e["size"]
        deleted = e["deleted"]

        # Instead of checking only the first 32 bytes, scan the cluster(s) for signatures
        actual_format = None

        if cluster_contains_jpeg(cluster):
            actual_format = "JPEG"
        elif cluster_contains_mp4(cluster):
            actual_format = "MP4"

        # ------------------------
        # Compare with extension
        # ------------------------
        mismatch = False

        if actual_format == "JPEG" and ext not in ("JPG", "JPEG"):
            mismatch = True

        if actual_format == "MP4" and ext not in ("MP4", "M4V", "MOV"):
            mismatch = True

        # Track deleted files
        if deleted:
            deleted_files.append({"name": name, "ext": ext, "cluster": cluster, "size": size})

        # Track MP4 files that don't have an MP4-like extension (regardless of deleted state)
        if actual_format == "MP4" and ext not in ("MP4", "M4V", "MOV"):
            mp4_wrong_ext.append({"name": name, "ext": ext, "cluster": cluster, "size": size, "deleted": deleted})

        # Track JPEG files that have an appropriate extension (regardless of deleted state)
        if actual_format == "JPEG" and ext in ("JPG", "JPEG"):
            jpeg_entry = {"name": name, "ext": ext, "cluster": cluster, "size": size, "deleted": deleted}
            jpeg_correct_ext.append(jpeg_entry)

            # Attempt extraction and save recovered file. Use cluster and name to build a unique filename.
            out_dir = "recovered_jpegs"
            os.makedirs(out_dir, exist_ok=True)
            safe_name = f"{name}_{cluster}.jpg"
            out_path = os.path.join(out_dir, safe_name)

            extracted = extract_jpeg_from_cluster(cluster, out_path)
            if extracted:
                jpeg_entry["recovered_path"] = out_path
            else:
                jpeg_entry["recovered_path"] = None

        # ------------------------
        # Print per-file findings (existing behaviour)
        # ------------------------
        print("-----")
        print(f"File: {name}.{ext} (cluster {cluster}, size {size})")
        print(f"Deleted: {'YES' if deleted else 'NO'}")

        if actual_format:
            print(f"Actual format detected: {actual_format}")
        else:
            print("Actual format: UNKNOWN / Not JPEG or MP4")

        if mismatch:
            print(" MISMATCH: File contents indicate a different format!")
        else:
            print("OK: Extension matches file content.")

        print("-----\n")

    # ----------------------------
    # Scan for embedded JPEGs (not just those with correct extension)
    # ----------------------------
    embedded_jpegs = scan_entire_image_for_jpeg()

    # ----------------------------
    # Summary Report
    # ----------------------------
    print("\n=== Summary Report ===")
    print(f"Total entries scanned: {len(entries)}")

    print(f"\nDeleted files ({len(deleted_files)}):")
    if deleted_files:
        for d in deleted_files:
            print(f"- {d['name']}.{d['ext']} (cluster {d['cluster']}, size {d['size']})")
    else:
        print("- None")

    print(f"\nMP4-formatted files with non-MP4 extension ({len(mp4_wrong_ext)}):")
    if mp4_wrong_ext:
        for m in mp4_wrong_ext:
            print(f"- {m['name']}.{m['ext']} (cluster {m['cluster']}, size {m['size']}, deleted={'YES' if m['deleted'] else 'NO'})")
    else:
        print("- None")

    print(f"\nJPEG-formatted files with correct JPEG extension ({len(jpeg_correct_ext) + len(embedded_jpegs)}):")
    if jpeg_correct_ext or embedded_jpegs:
        for j in jpeg_correct_ext:
            print(f"- {j['name']}.{j['ext']} (cluster {j['cluster']}, size {j['size']}, deleted={'YES' if j['deleted'] else 'NO'})")
        for cluster_num, offset in embedded_jpegs:
            # Try to find a matching entry by cluster
            match = next((e for e in entries if e["cluster"] == cluster_num), None)
            if match:
                print(f"- {match['name']}.{match['ext']} (cluster {cluster_num}, offset {offset})")
            else:
                print(f"- [EMBEDDED] Cluster {cluster_num}, Offset {offset}")
    else:
        print("- None")

    print(f"\nEmbedded JPEG signatures found ({len(embedded_jpegs)}):")
    if embedded_jpegs:
        for cluster_num, offset in embedded_jpegs:
            print(f"- Cluster {cluster_num}, Offset {offset}")
    else:
        print("- None")

    print("\n=== End of Report ===\n")


# ----------------------------
# RUN ANALYZER
# ----------------------------
analyze_files()
