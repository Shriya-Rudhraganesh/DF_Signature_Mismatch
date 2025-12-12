#!/usr/bin/env python3
import argparse
from disk_parser import DiskParser
from fat32_parser import FAT32Parser
from signature_scanner import SignatureScanner
from recovery import Recovery
from reporter import generate_report

def main():
    parser = argparse.ArgumentParser(description="FAT32 deleted-file scanner & basic recovery tool")
    parser.add_argument("image", help="Path to raw disk image (e.g., disk.img)")
    parser.add_argument("--list", action="store_true", help="List directory entries (including deleted)")
    parser.add_argument("--scan-sigs", action="store_true", help="Scan files for MP4/JPEG signatures and detect mismatches")
    parser.add_argument("--recover", metavar="ENTRY_INDEX", type=int, help="Recover file by index from list (0-based)")
    parser.add_argument("--report", metavar="OUT", default="report.csv", help="Write CSV report")
    args = parser.parse_args()

    dp = DiskParser(args.image)
    fat = FAT32Parser(dp)
    entries = fat.scan_root_dir_recursive()
    sigscanner = SignatureScanner()
    checks = {}

    if args.list or args.scan_sigs or args.report:
        print(f"Found {len(entries)} directory entries (this tool may include empty/non-used slots).")
        for idx, e in enumerate(entries):
            status = "DELETED" if e.deleted else "LIVE"
            ext_display = f".{e.ext}" if e.ext else ""
            print(f"[{idx}] {status}: {e.name}{ext_display} size={e.filesize} cluster={e.first_cluster}")

    if args.scan_sigs or args.report:
        for idx, e in enumerate(entries):
            if e.first_cluster and e.filesize:
                try:
                    # compute file start offset (same as in Recovery)
                    start = fat._cluster_to_offset(e.first_cluster)
                    data = dp.read_bytes(start, min(4096, e.filesize))
                    sig = sigscanner.detect(data)
                    checks[e.entry_offset] = sig
                    # Report mismatches
                    if sig:
                        ext_upper = (e.ext or "").upper()
                        if ext_upper in ("JPG", "JPEG") and sig != "JPEG":
                            print(f"  -> signature mismatch at index {idx}: file says .{e.ext} but signature {sig}")
                        if ext_upper in ("MP4", "M4V", "MOV") and sig != "MP4":
                            print(f"  -> signature mismatch at index {idx}: file says .{e.ext} but signature {sig}")
                except Exception as ex:
                    checks[e.entry_offset] = None

    if args.report:
        report_path = generate_report(entries, checks, out=args.report)
        print("Report written to", report_path)

    if args.recover is not None:
        idx = args.recover
        if idx < 0 or idx >= len(entries):
            print("Invalid index to recover.")
            return
        e = entries[idx]
        if not e.first_cluster or e.filesize == 0:
            print("Cannot recover: missing cluster or size 0.")
            return
        rec = Recovery(dp)
        out = rec.recover_by_cluster(e.first_cluster, e.filesize, fat.bpb, f"recovered_{idx}_{e.name}.{e.ext or 'bin'}")
        print("Recovered to", out)

if __name__ == "__main__":
    main()
