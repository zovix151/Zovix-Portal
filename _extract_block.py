# Read lines around line 14945 from app.py and save to output file
with open(r"c:\Zovix-Clean\app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

start = 14900
end = 15000
with open(r"c:\Zovix-Clean\_extracted_lines.txt", "w", encoding="utf-8") as out:
    for i in range(start - 1, min(end, len(lines))):
        out.write(f"{i+1}: {lines[i]}")
print(f"Wrote lines {start}-{end} to _extracted_lines.txt. Total lines in file: {len(lines)}")