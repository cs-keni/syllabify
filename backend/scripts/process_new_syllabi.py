"""
Process PDFs from new-syllabus: extract text, create folders, generate parsed.json.
Run: cd backend && PYTHONPATH=. python scripts/process_new_syllabi.py

Creates:
  - extracted/{course_id}.txt (extracted text)
  - syllabus/{course_id}/{original.pdf} (copy of PDF)
  - syllabus/{course_id}/parsed.json (parsed output from syllabus_parser)
"""
import json
import re
import shutil
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
NEW_SYLLABUS = BACKEND / "tests" / "fixtures" / "syllabus-data" / "new-syllabus"
EXTRACTED = BACKEND / "tests" / "fixtures" / "syllabus-data" / "extracted"
SYLLABUS_ROOT = BACKEND / "tests" / "fixtures" / "syllabus-data" / "syllabus"


# Explicit filename -> course_id for known bad derivations
_FILENAME_TO_COURSE_ID = {
    "PHYSICS 345 syllabus.pdf": "PHY345",
    "Physics 345 syllabus.pdf": "PHY345",
    "BA324_B-Comm_Syllabus_S2024.pdf": "BA324",
    "handout375R.pdf": "PHY375R",
    "Physics_N317K_Summer2017_Syllabus.pdf": "PHY317K",
    "spring17.pdf": "PHY387K",
    "Spring17_QM_Syllabus.pdf": "PHY387K-QM",
    "Syllabus-FallX2014.pdf": "CS395T",
    "Syllabus_BCI-course_Fall2024.pdf": "EE385J",
    "syllfor354.pdf": "CH354",
}


def derive_course_id_from_filename(name: str) -> str:
    """Derive a folder/course ID from filename. E.g. 'CH 204 - Lyon.pdf' -> CH204-Lyon."""
    if name in _FILENAME_TO_COURSE_ID:
        return _FILENAME_TO_COURSE_ID[name]
    stem = Path(name).stem
    stem = re.sub(r"\[1\]$", "", stem, flags=re.I)
    # PHYSICS/PHY prefix: "PHYSICS 345" -> PHY345 (before generic DEPT+NUM)
    m = re.search(r"PHYSICS?\s*(\d{2,3}[A-Z]?)", stem, re.I)
    if m:
        return f"PHY{m.group(1)}"
    # DEPT + NUM: "CH 204 - Lyon", "FIN 377.1 - Kamm", "BA-285T", "MKT 337", "ECE 396N"
    m = re.search(r"([A-Z]{2,4})[\s\-]*(\d{2,3}[A-Z]?(?:\.\d+)?)", stem, re.I)
    if m:
        dept = m.group(1).upper()
        num = m.group(2).replace(".", "_").replace(" ", "")
        rest = stem[m.end():].strip()
        parts = re.split(r"[,–\-]", rest)
        extra = ""
        for p in parts[:2]:
            p = p.strip()
            if 2 <= len(p) <= 20 and not p.lower().startswith(("syllabus", "fall", "spring", "summer", "financial")):
                w = p.replace(" ", "_")
                if re.match(r"^[\w]+$", w):
                    extra = "-" + w
                    break
        return f"{dept}{num}{extra}" if extra else f"{dept}{num}"
    # Instructor_Num: "Batory_373S", "Qiu_356R", "Downing_109"
    m = re.search(r"^([A-Za-z]+)_(\d{2,3}[A-Z]?)$", stem, re.I)
    if m:
        return f"{m.group(2)}-{m.group(1)}"
    # Num_Course: "395L_Spring_2017_syllabus" -> 395L
    m = re.search(r"^(\d{2,3}[A-Z]?)_", stem, re.I)
    if m:
        return m.group(1)
    # Leading num: "07770-Quigley" -> 07770-Quigley (unique section+instructor)
    m = re.search(r"^(\d{5})[\-\_]([A-Za-z]+)", stem, re.I)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    # Numeric only: "17915", "92028" -> use stem as-is
    if re.match(r"^\d+$", stem):
        return stem
    # Generic: sanitize
    safe = re.sub(r"[^\w\s\-]", "", stem)
    safe = re.sub(r"\s+", "_", safe)[:35]
    return safe or "unknown"


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using document_utils."""
    from app.utils.document_utils import extract_text_from_file
    with open(pdf_path, "rb") as f:
        content = f.read()
    class FileLike:
        def __init__(self, data, name):
            self._data = data
            self._pos = 0
            self.filename = name
        def read(self, n=-1):
            if n == -1:
                r = self._data[self._pos:]
                self._pos = len(self._data)
            else:
                r = self._data[self._pos:self._pos+n]
                self._pos += len(r)
            return r
        def seek(self, pos):
            self._pos = pos
    f = FileLike(content, pdf_path.name)
    return extract_text_from_file(f)


def process_pdf(pdf_path: Path, dry_run: bool = False) -> str | None:
    """
    Process one PDF: extract, create folder, copy PDF, parse, save parsed.json.
    Returns course_id on success, None on skip/error.
    """
    course_id = derive_course_id_from_filename(pdf_path.name)
    # Avoid overwriting existing; skip if course_id already in syllabus
    if (SYLLABUS_ROOT / course_id).exists() and (SYLLABUS_ROOT / course_id / "parsed.json").exists():
        return None  # Skip - already processed
    try:
        text = extract_text_from_pdf(pdf_path)
    except Exception as e:
        print(f"  ERR extract {pdf_path.name}: {e}")
        return None
    if not text or len(text.strip()) < 100:
        print(f"  SKIP {pdf_path.name}: too little text extracted")
        return None
    if dry_run:
        print(f"  Would process: {pdf_path.name} -> {course_id}")
        return course_id
    # Create extracted txt
    extracted_path = EXTRACTED / f"{course_id}.txt"
    extracted_path.write_text(text, encoding="utf-8", errors="replace")
    # Create syllabus folder and copy PDF
    folder = SYLLABUS_ROOT / course_id
    folder.mkdir(parents=True, exist_ok=True)
    dest_pdf = folder / pdf_path.name
    shutil.copy2(pdf_path, dest_pdf)
    # Parse with full syllabus_parser
    from app.services.syllabus_parser import parse_syllabus_text
    source_type = "pdf"
    result = parse_syllabus_text(text, course_id, source_type)
    result["metadata"]["source_type"] = source_type
    out = folder / "parsed.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  OK {pdf_path.name} -> {course_id} ({len(result.get('assessments', []))} assessments)")
    return course_id


def main():
    import sys
    dry = "--dry" in sys.argv
    limit = None
    for a in sys.argv:
        if a.startswith("--limit="):
            limit = int(a.split("=")[1])
    if not NEW_SYLLABUS.exists():
        NEW_SYLLABUS.mkdir(parents=True, exist_ok=True)
        print("Created new-syllabus/ (empty). Add PDFs there and run again.")
        return
    pdfs = sorted(NEW_SYLLABUS.glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in new-syllabus/")
        return
    print(f"Processing {len(pdfs)} PDFs from new-syllabus/")
    done = 0
    for p in pdfs:
        if limit and done >= limit:
            break
        r = process_pdf(p, dry_run=dry)
        if r:
            done += 1
    print(f"Done: {done} processed")


if __name__ == "__main__":
    main()
