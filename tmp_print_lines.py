import sys

def print_range(path, start, end, label=""):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    print(f"\n===== {label} ({path}) lines {start}-{end} =====")
    for i in range(start-1, min(end, len(lines))):
        print(f"{i+1}: {lines[i]}", end="")

if __name__ == "__main__":
    # current app.py generate_face_video
    print_range("app.py", 6876, 7130, "CURRENT app.py generate_face_video area")
