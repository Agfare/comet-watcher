# Automated COMET Score Evaluator

This Python script is a real-time tool for evaluating machine translation (MT) quality using the **COMET** metric. It watches a specified folder for new `.txt` files and automatically processes them, calculating a COMET score for each translation. The results are logged to JSONL files and compiled into a clean, human-readable HTML report.

The script is ideal for developers, researchers, and localization engineers who need to continuously monitor the quality of MT outputs.

---

## 🚀 Features

* **Folder Watching**: Automatically detects new `.txt` files in a designated input folder.
* **Real-time Evaluation**: Processes each new translation file on the fly using the powerful `Unbabel/wmt22-comet-da` model.
* **Threshold-based Warnings**: Flags translations that fall below a configurable quality threshold.
* **Detailed Logging**: Records all evaluation results to `comet_scores.jsonl` and warnings to `warnings.jsonl`.
* **Live HTML Report**: Generates a dynamic `report.html` file that provides a clear overview of all results, including a summary dashboard and a list of low-scoring translations.
* **Batch Processing**: Evaluates existing files in the input folder when the script starts.

---

## ⚙️ How It Works

1.  **Start the Script**: Run the main script. It will begin by processing any existing `.txt` files in the `./translations` directory.
2.  **Add a Translation**: Create a new `.txt` file in the `./translations` folder. The file should contain:
    * **Line 1**: The source sentence.
    * **Line 2**: The machine translation (MT) output.
    * **Line 3 (Optional)**: A human-generated reference translation.

    *Example: `example.txt`*

    ```
    The quick brown fox jumps over the lazy dog.
    Der schnelle braune Fuchs springt über den faulen Hund.
    Der flinke braune Fuchs springt über den faulen Hund.
    ```

3.  **Automatic Evaluation**: The script detects the new file, calculates its COMET score, and logs the result.
4.  **View the Report**: The `report.html` file is automatically updated. You can open it in any web browser to see the latest results. You can even set it to auto-refresh for a live view.

---

## 🔧 Configuration

You can customize the script's behavior by editing the constants at the top of the `main.py` file.

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `INPUT_FOLDER` | The folder to watch for new `.txt` files. | `./translations` |
| `OUTPUT_FILE` | The path for the main JSONL log file. | `./comet_scores.jsonl` |
| `WARNING_FILE` | The path for the warnings-only JSONL log file. | `./warnings.jsonl` |
| `REPORT_FILE` | The path for the generated HTML report. | `./report.html` |
| `MODEL_NAME` | The COMET model to use for evaluation. | `"Unbabel/wmt22-comet-da"` |
| `WARNING_THRESHOLD` | The minimum COMET score considered acceptable. | `0.8` |
| `AUTO_REFRESH_SECONDS`| Set to a positive number for the HTML report to auto-refresh. Set to `0` to disable. | `0` |

---

## 📦 Installation & Usage

### Prerequisites

* Python 3.8+
* [`watchdog`](https://pypi.org/project/watchdog/): A library for monitoring file system events.
* [`unbabel-comet`](https://pypi.org/project/unbabel-comet/): The library for calculating COMET scores.

### Steps

1.  **Clone the Repository**:
    ```bash
    git clone [https://github.com/your-username/your-repo.git](https://github.com/your-username/your-repo.git)
    cd your-repo
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Script**:
    ```bash
    python main.py
    ```

The script will now be running, and you'll see a console output confirming that it's watching the specified folder. To stop the script, press `Ctrl+C`.