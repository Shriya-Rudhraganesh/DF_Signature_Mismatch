import os

class Recovery:
    def __init__(self, disk_parser):
        self.dp = disk_parser
        os.makedirs('recovered', exist_ok=True)

    def recover_by_cluster(self, start_cluster: int, size: int, bpb, out_name: str) -> str:
        """Recover contiguous data starting at start_cluster reading `size` bytes.
        This does NOT follow FAT chains — it assumes file is contiguous/unfragmented."""
        if start_cluster == 0:
            raise ValueError("Start cluster is zero; cannot recover.")

        data_region_sector = bpb.reserved_sector_count + (bpb.num_fats * bpb.fat_size_32)
        offset = (data_region_sector + (start_cluster - 2) * bpb.sectors_per_cluster) * bpb.bytes_per_sector
        data = self.dp.read_bytes(offset, size)
        out_path = os.path.join('recovered', out_name)
        with open(out_path, 'wb') as f:
            f.write(data)
        return os.path.abspath(out_path)
