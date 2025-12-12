import struct
from dataclasses import dataclass

@dataclass
class FAT32BPB:
    bytes_per_sector: int
    sectors_per_cluster: int
    reserved_sector_count: int
    num_fats: int
    fat_size_32: int
    root_cluster: int
    total_sectors: int

class DiskParser:
    def __init__(self, image_path: str):
        self.image_path = image_path

    def read_bytes(self, offset: int, size: int) -> bytes:
        """Read `size` bytes starting at `offset` from the raw image."""
        with open(self.image_path, "rb") as f:
            f.seek(offset)
            return f.read(size)

    def read_struct(self, offset: int, fmt: str):
        size = struct.calcsize(fmt)
        data = self.read_bytes(offset, size)
        return struct.unpack(fmt, data)

    def detect_fat32_bpb(self) -> FAT32BPB:
        """Parse the FAT32 BIOS Parameter Block (BPB) at offset 0."""
        b = self.read_bytes(0, 512)
        if len(b) < 512:
            raise ValueError("Image too small or unreadable to read BPB (need 512 bytes).")

        bytes_per_sector = int.from_bytes(b[11:13], "little")
        sectors_per_cluster = b[13]
        reserved_sector_count = int.from_bytes(b[14:16], "little")
        num_fats = b[16]
        total_sectors_16 = int.from_bytes(b[19:21], "little")
        total_sectors_32 = int.from_bytes(b[32:36], "little")
        fat_size_16 = int.from_bytes(b[22:24], "little")
        fat_size_32 = int.from_bytes(b[36:40], "little")
        root_cluster = int.from_bytes(b[44:48], "little")

        total_sectors = total_sectors_32 if total_sectors_32 != 0 else total_sectors_16
        fat_size = fat_size_32 if fat_size_32 != 0 else fat_size_16

        return FAT32BPB(
            bytes_per_sector=bytes_per_sector,
            sectors_per_cluster=sectors_per_cluster,
            reserved_sector_count=reserved_sector_count,
            num_fats=num_fats,
            fat_size_32=fat_size,
            root_cluster=root_cluster,
            total_sectors=total_sectors
        )
