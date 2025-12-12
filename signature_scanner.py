# Signature scanner for JPEG and MP4 (ftyp) patterns.

MP4_SIGS = [
    bytes.fromhex('0000001866747970'),        # common MP4 ftyp header (32-bit size + 'ftyp')
    bytes.fromhex('000000146674797069736f6d')  # smaller variant with 'isom' brand
]
JPEG_SIG = bytes.fromhex('FFD8FF')

class SignatureScanner:
    def __init__(self):
        pass

    def detect(self, data: bytes):
        """Return a short signature label ('JPEG'|'MP4') or None."""
        if not data:
            return None
        if data.startswith(JPEG_SIG):
            return 'JPEG'
        for s in MP4_SIGS:
            if data.startswith(s):
                return 'MP4'
        return None
