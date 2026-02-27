"""Extract text from all syllabus files (PDF, DOCX, TXT) for analysis."""
import json
import os
import sys

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.document_utils import extract_text_from_file

SYLLABUS_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "tests", "fixtures", "syllabus-data", "syllabus"
)


def main():
    out_dir = os.path.join(SYLLABUS_ROOT, "..", "extracted")
    os.makedirs(out_dir, exist_ok=True)

    results = {}
    for entry in os.listdir(SYLLABUS_ROOT):
        folder = os.path.join(SYLLABUS_ROOT, entry)
        if not os.path.isdir(folder):
            continue
        # Find syllabus file (first non-hidden file that's not target.txt)
        for f in os.listdir(folder):
            if f.startswith(".") or f == "target.txt" or f == "parsed.json":
                continue
            path = os.path.join(folder, f)
            if os.path.isfile(path):
                try:
                    with open(path, "rb") as fp:
                        fp.filename = f
                        text = extract_text_from_file(fp)
                    results[entry] = {"file": f, "text": text[:8000]}
                    out_path = os.path.join(out_dir, f"{entry}.txt")
                    with open(out_path, "w", encoding="utf-8") as fp:
                        fp.write(text)
                    print(f"OK {entry}: {f} -> {len(text)} chars")
                except Exception as e:
                    print(f"ERR {entry}: {e}")
                    results[entry] = {"file": f, "error": str(e)}
                break

    summary_path = os.path.join(out_dir, "_index.json")
    with open(summary_path, "w", encoding="utf-8") as fp:
        idx = {k: {"file": v["file"], "ok": "error" not in v} for k, v in results.items()}
        json.dump(idx, fp, indent=2)
    print(f"\nExtracted {len(results)} syllabi to {out_dir}")


if __name__ == "__main__":
    main()
