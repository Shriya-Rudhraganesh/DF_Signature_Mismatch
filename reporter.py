import os
try:
    import pandas as pd
except Exception:
    pd = None

def generate_report(entries, checks, out='report.csv'):
    """Generate a CSV report of scanned entries and signature checks.

    entries: iterable of DirEntry
    checks: dict mapping entry.entry_offset -> signature string or None
    """
    rows = []
    for e in entries:
        sig = checks.get(e.entry_offset)
        display_name = f"{e.name}.{e.ext}" if e.ext else e.name
        rows.append({
            "name": display_name,
            "deleted": bool(e.deleted),
            "first_cluster": int(e.first_cluster),
            "filesize": int(e.filesize),
            "signature": sig or ""
        })
    if pd:
        df = pd.DataFrame(rows)
        df.to_csv(out, index=False)
    else:
        # Fallback to manual CSV if pandas not installed
        with open(out, 'w', newline='') as f:
            headers = ["name","deleted","first_cluster","filesize","signature"]
            f.write(",".join(headers) + "\n")
            for r in rows:
                line = f"{r['name']},{int(r['deleted'])},{r['first_cluster']},{r['filesize']},{r['signature']}\n"
                f.write(line)
    return os.path.abspath(out)
