from dataclasses import dataclass
from typing import List
from disk_parser import DiskParser

@dataclass
class DirEntry:
    raw_name: bytes
    name: str
    ext: str
    attr: int
    first_cluster: int
    filesize: int
    deleted: bool
    entry_offset: int

class FAT32Parser:
    def __init__(self, disk_parser: DiskParser):
        self.dp = disk_parser
        self.bpb = self.dp.detect_fat32_bpb()

    def _cluster_to_offset(self, cluster: int) -> int:
        """Convert a cluster number to an offset in bytes to the start of that cluster's data."""
        data_region_sector = self.bpb.reserved_sector_count + (self.bpb.num_fats * self.bpb.fat_size_32)
        offset = (data_region_sector + (cluster - 2) * self.bpb.sectors_per_cluster) * self.bpb.bytes_per_sector
        return offset

    def scan_root_dir_recursive(self) -> List[DirEntry]:
        """
        Read directory entries starting from the root cluster.
        NOTE: This simplified scanner reads a fixed number of clusters from the root cluster area.
        It will detect deleted entries (0xE5 first byte) and live entries. It does NOT follow FAT chains.
        """
        entries: List[DirEntry] = []
        root = self.bpb.root_cluster
        # Safety limit: how many clusters of the root directory region to inspect
        clusters_to_read = 64

        for i in range(clusters_to_read):
            cluster = root + i
            offset = self._cluster_to_offset(cluster)
            size = self.bpb.sectors_per_cluster * self.bpb.bytes_per_sector
            data = self.dp.read_bytes(offset, size)
            if not data:
                continue
            for j in range(0, len(data), 32):
                entry = data[j:j+32]
                if len(entry) < 32:
                    continue
                first_byte = entry[0]
                if first_byte == 0x00:
                    # 0x00 marks: no more entries in this directory table region
                    break
                # Long File Name (LFN) entries have attribute 0x0F; skip them for this simple parser
                attr = entry[11]
                if attr == 0x0F:
                    continue

                raw_name = entry[0:11]
                deleted = (first_byte == 0xE5)

                # First cluster (high + low)
                first_cluster_high = int.from_bytes(entry[20:22], "little")
                first_cluster_low = int.from_bytes(entry[26:28], "little")
                first_cluster = (first_cluster_high << 16) | first_cluster_low
                filesize = int.from_bytes(entry[28:32], "little")

                # Parse name and ext carefully; if deleted, first character replaced
                if deleted:
                    # Replace the first character with '?' to indicate deleted name
                    name_bytes = bytes([ord('?')]) + raw_name[1:8]
                else:
                    name_bytes = raw_name[0:8]
                try:
                    name = name_bytes.decode("ascii", errors="replace").rstrip()
                except Exception:
                    name = repr(name_bytes)
                try:
                    ext = raw_name[8:11].decode("ascii", errors="replace").rstrip()
                except Exception:
                    ext = ""

                entries.append(DirEntry(
                    raw_name=raw_name,
                    name=name,
                    ext=ext,
                    attr=attr,
                    first_cluster=first_cluster,
                    filesize=filesize,
                    deleted=deleted,
                    entry_offset=offset + j
                ))
        return entries
