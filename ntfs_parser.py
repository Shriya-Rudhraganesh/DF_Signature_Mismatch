class NTFSParser:
    def __init__(self, disk_parser):
        self.dp = disk_parser

    def scan_mft(self):
        """NTFS MFT parsing is nontrivial. This is a stub to be implemented later."""
        raise NotImplementedError("NTFS scanning not implemented in this teaching skeleton.")
