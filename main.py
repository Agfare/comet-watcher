import os
import time
import json
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from comet import download_model, load_from_checkpoint

####################################
# CONFIGURATION
####################################
INPUT_FOLDER = "./translations"       # Folder containing .txt files
OUTPUT_FILE = "./comet_scores.jsonl"  # Log file path
WARNING_FILE = "./warnings.jsonl"     # Separate warning log file
SKIPPED_FILE = "./skipped.jsonl"      # Log for skipped files
REPORT_FILE = "./report.html"         # Human-friendly HTML report
MODEL_NAME = "Unbabel/wmt22-comet-da" # COMET model to use
WARNING_THRESHOLD = 0.8               # Minimum acceptable COMET score
AUTO_REFRESH_SECONDS = 0              # >0 to auto-refresh HTML (e.g., 10). 0 disables.
####################################

# Force single-threaded mode to avoid multiprocessing errors
os.environ["COMET_NUM_WORKERS"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

# ANSI escape codes for colored output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

# Load COMET model once
model_path = download_model(MODEL_NAME)
model = load_from_checkpoint(model_path)

# In-memory dictionaries to hold unique records
all_results = {}
skipped_records = {}

# Utilities
def _read_jsonl(path):
    if not os.path.exists(path):
        return {}
    
    records = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    file_key = record.get("file", "unknown")
                    # Use a combination of file name and a simple hash of content for a unique key
                    content_hash = hash(record.get("source", "") + record.get("mt_output", ""))
                    key = f"{file_key}:{content_hash}"
                    records[key] = record
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from {path}: {e}")
    return records

def _write_jsonl(data_dict, path):
    with open(path, "w", encoding="utf-8") as f:
        for record in data_dict.values():
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

# HTML report generator
def generate_html_report():
    results = list(all_results.values())
    warnings = [r for r in results if r.get("warning")]
    skipped = list(skipped_records.values())

    total = len(results)
    warn_count = len(warnings)
    avg = round(sum(r.get("comet_score", 0.0) for r in results) / total, 4) if total else 0.0
    updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    meta_refresh = f'<meta http-equiv="refresh" content="{AUTO_REFRESH_SECONDS}">\n' if AUTO_REFRESH_SECONDS > 0 else ""

    def row(r):
        score = r.get("comet_score", 0.0)
        cls = "ok" if score >= WARNING_THRESHOLD else "bad"
        src = (r.get("source") or "").replace("<", "&lt;")
        mt = (r.get("mt_output") or "").replace("<", "&lt;")
        ref = (r.get("reference") or "").replace("<", "&lt;")
        fname = (r.get("file") or "").replace("<", "&lt;")
        return f"<tr><td class=mono>{fname}</td><td>{src}</td><td>{mt}</td><td>{ref}</td><td class='score {cls}'>{score:.4f}</td></tr>"

    rows_html = "\n".join(row(r) for r in results)
    warn_rows = "\n".join(row(r) for r in warnings)

    skipped_rows = "\n".join(
        f"<tr><td class=mono>{(s.get('file') or '').replace('<','&lt;')}</td><td>{(s.get('reason') or '').replace('<','&lt;')}</td><td class=mono>{(str(s.get('lines')) or '').replace('<','&lt;')}</td></tr>"
        for s in skipped
    )

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">{meta_refresh}<meta name="viewport" content="width=device-width, initial-scale=1">
<title>COMET Report</title>
<style>
  :root {{ --warn:{WARNING_THRESHOLD}; }}
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #111; }}
  h1 {{ margin: 0 0 4px 0; }}
  .sub {{ color:#666; margin-bottom: 16px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 12px; margin: 12px 0 20px; }}
  .card {{ background:#f8f9fb; border:1px solid #e6e8ee; border-radius:12px; padding:14px; box-shadow: 0 1px 2px rgba(0,0,0,.03); }}
  .kpi {{ font-size: 26px; font-weight: 700; }}
  .kpi small {{ font-size: 12px; font-weight: 500; color:#555; margin-left: 6px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border-bottom: 1px solid #eee; padding: 8px 10px; vertical-align: top; }}
  th {{ text-align: left; background:#fafbfc; position: sticky; top: 0; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; white-space: nowrap; }}
  .score {{ text-align:right; font-weight: 700; }}
  .score.ok {{ color: #0a773a; }}
  .score.bad {{ color: #b00020; }}
  .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; font-weight:600; }}
  .pill.ok {{ background:#e9f7ef; color:#0a773a; }}
  .pill.bad {{ background:#fdecea; color:#b00020; }}
  details {{ margin: 10px 0 18px; }}
  summary {{ cursor: pointer; font-weight: 600; }}
  footer {{ color:#777; font-size:12px; margin-top:22px; }}
</style>
</head>
<body>
  <h1>COMET Report</h1>
  <div class=sub>Updated: {updated} • Model: <code>{MODEL_NAME}</code> • Threshold: <b>{WARNING_THRESHOLD}</b></div>

  <div class=cards>
    <div class=card><div class=kpi>{total}</div><div>Total evaluated</div></div>
    <div class=card><div class=kpi>{warn_count} <span class="pill bad">below</span></div><div>Below threshold</div></div>
    <div class=card><div class=kpi>{avg:.4f}</div><div>Average score</div></div>
  </div>

  <h2>All Results</h2>
  <table>
    <thead>
      <tr><th>File</th><th>Source</th><th>MT Output</th><th>Reference</th><th>Score</th></tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>

  <details {"open" if warn_count else ""}>
    <summary>⚠️ Warnings (below {WARNING_THRESHOLD}) — {warn_count}</summary>
    <table>
      <thead><tr><th>File</th><th>Source</th><th>MT Output</th><th>Reference</th><th>Score</th></tr></thead>
      <tbody>
        {warn_rows}
      </tbody>
    </table>
  </details>

  <details>
    <summary>⏭️ Skipped files — {len(skipped)}</summary>
    <table>
      <thead><tr><th>File</th><th>Reason</th><th>Lines</th></tr></thead>
      <tbody>
        {skipped_rows}
      </tbody>
    </table>
  </details>

  <footer>Generated automatically by the folder watcher. Open this file directly in your browser.{' Auto-refresh is on.' if AUTO_REFRESH_SECONDS>0 else ''}</footer>
</body>
</html>
"""

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

def save_and_report():
    """Rewrites the log files and regenerates the HTML report."""
    _write_jsonl(all_results, OUTPUT_FILE)
    _write_jsonl({k:v for k,v in all_results.items() if v.get('warning')}, WARNING_FILE)
    _write_jsonl(skipped_records, SKIPPED_FILE)
    generate_html_report()

def process_file(file_path):
    """Processes a single .txt file and updates the in-memory dictionaries."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        file_basename = os.path.basename(file_path)
        
        # Expecting 2 or 3 lines: source, mt_output, [optional reference]
        if len(lines) < 2:
            print(f"{YELLOW}⚠️ Skipping {file_basename} (needs at least source + MT output){RESET}")
            skipped_record = {
                "file": file_basename,
                "reason": "Insufficient lines",
                "lines": lines
            }
            # Add or update the skipped record
            skipped_records[file_basename] = skipped_record
            save_and_report()
            return

        src, mt = lines[0], lines[1]
        ref = lines[2] if len(lines) > 2 else None
        
        data = [{
            "src": src,
            "mt": mt,
            "ref": ref
        }]

        # Call predict without extra kwargs (safe mode)
        score = model.predict(data).system_score
        score_rounded = round(score, 4)
        
        record_key = f"{file_basename}:{hash(src + mt)}"
        record = {
            "file": file_basename,
            "source": src,
            "mt_output": mt,
            "reference": ref,
            "comet_score": score_rounded,
            "warning": score_rounded < WARNING_THRESHOLD
        }

        # Add or update the main result record
        all_results[record_key] = record

        if record["warning"]:
            print(f"{RED}⚠️ WARNING: {file_basename} scored {score_rounded:.4f}, below threshold {WARNING_THRESHOLD}!{RESET}")
        else:
            print(f"{GREEN}Processed {file_basename} → COMET score: {score_rounded:.4f}{RESET}")

        # Remove from skipped if it was there before
        if file_basename in skipped_records:
            del skipped_records[file_basename]
            
        save_and_report()

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

# File watcher
class TranslationHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".txt"):
            print(f"{CYAN}Detected new file: {event.src_path}{RESET}")
            process_file(event.src_path)
            
    def on_modified(self, event):
        # Also handle modifications to existing files
        if not event.is_directory and event.src_path.endswith(".txt"):
            print(f"{CYAN}Detected file modification: {event.src_path}{RESET}")
            process_file(event.src_path)

# Batch process existing files
def batch_process():
    print(f"Running batch processing on existing files in {INPUT_FOLDER}...")
    for fname in os.listdir(INPUT_FOLDER):
        if fname.endswith(".txt"):
            fpath = os.path.join(INPUT_FOLDER, fname)
            process_file(fpath)

if __name__ == "__main__":
    os.makedirs(INPUT_FOLDER, exist_ok=True)
    
    # Load existing data at startup
    all_results = _read_jsonl(OUTPUT_FILE)
    skipped_records = _read_jsonl(SKIPPED_FILE)
    
    batch_process()
    
    print(f"Watching folder: {INPUT_FOLDER}")
    observer = Observer()
    event_handler = TranslationHandler()
    observer.schedule(event_handler, INPUT_FOLDER, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"{YELLOW}Shutting down...{RESET}")
        observer.stop()
        observer.join()
        save_and_report()
        print(f"{GREEN}Shutdown complete. Report updated.{RESET}")