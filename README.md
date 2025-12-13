# DF_Signature_Mismatch
Deleted File recovery using Signature Mismatch
This Python script performs forensic analysis on a FAT32 disk image:
1)Parse directory entries
2)Identify deleted files
3)Detect actual file formats using file signatures
4)Recover JPEG images/ PNG images
5)Detect embedded (orphaned) JPEG files not referenced by directory entries

whole.py code explained step by step:
line 1 2 imports:
struct: Used to unpack raw binary data (Since i have used Binary pattern matching)
os: Used for directory creation and file handling
line 4: The FAT32 disk image file being analyzed
line 6-9: Defines the FAT32 layout:
line 10:Boot sector size
FAT table size (two FATs assumed)
Root directory region size
Cluster size
line 17-26 signature defination:
JPEG start-of-image (SOI) signature or Checks whether data starts with JPEG signature or Checks whether data starts with MP4 signature
line 33 -93: Scanning Entire Image for Embedded JPEGs
line 100-164: read the file header by clusters bytes
Scanning Entire Image for Embedded JPEGs
Scans all data clusters, not just directory-referenced files
Used to find orphaned or carved JPEGs
Reads one cluster at a time
Searches for JPEG signature inside the cluster
Reports physical offset and cluster number
Calculates root directory start
Each FAT directory entry is exactly 32 byte
In case if the scan is going out of boundry it keeps last 1MB in case marker crosses boundary.
Analysis and Mislabel Detection:
line 173-189:Added cluster scan helper collection for summary report, Scan the cluster for signatures.
Compare with extension.
line 222 track deleted files:line 230 Track JPEG files that have an appropriate extension (regardless of deleted state)
line 236 Attempt extraction and save recovered file. Use cluster and name to build a unique filename.
line 250-264 prints file findings
line 269 Scan for embedded JPEGs (not just those with correct extension)
line 274 to 312 summary of the report 
line 316 Run analysis 
