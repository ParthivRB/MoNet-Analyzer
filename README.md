# MoNet Analyzer

This repository provides a streamlined, portable Graphical User Interface (GUI) wrapper for the **MoNet** deep learning model. It allows for high-throughput classification of microparticle trajectories into physical motion types (Brownian, FBM, CTRW). This setup ensures strict data hygiene, precise filtering, and seamless compatibility with downstream tools like MPTHub.

-----

## ✨ Features

  * **GUI Interface:** Easily manage input datasets and filtering modes via a clean Tkinter GUI (`main.py`).
  * **Deep Learning Integration:** Automated backend handling of the Keras/TensorFlow model (`FINALmodel_300.h5`) to classify trajectories based on 300-frame geometric signatures.
  * **Smart Column Detection:** The engine automatically identifies trajectory data columns (e.g., "Track ID" vs "Trajectory", "x" vs "Position X") regardless of input formatting variations.
  * **Non-Destructive Processing:** Analyzes data on a copy but saves results using the **exact** original file structure and headers, ensuring compatibility with strict downstream software.
  * **Intelligent Filtering:** Automatically skips and logs files that contain 0 trajectories of the selected motion type to prevent empty file errors in subsequent analysis.
  * **Hacker-Style Logging:** Features a dark-mode log window with live status emojis (🚀, 🧠, ✅, ❌) for at-a-glance monitoring.

-----

## ⚙️ Setup and Installation

### Prerequisites

1.  **Python 3.10+:** Required for TensorFlow/Keras compatibility.
2.  **MoNet Model File:** You must download `FINALmodel_300.h5` from the original MoNet repository and place it in the `models/` folder.

### Installation Steps

1.  **Clone or Download:** Get the contents of this repository onto your machine.

2.  **Open Terminal:** Navigate into the main project directory.

3.  **Create and Activate Virtual Environment (Recommended)**

    ```bash
    # 1. Create the environment
    python3 -m venv .venv

    # 2. Activate the environment
    # Mac/Linux:
    source .venv/bin/activate
    # Windows:
    # .venv\Scripts\activate
    ```

4.  **Install Dependencies**

    ```bash
    # This installs TensorFlow, Pandas, Keras, etc.
    pip install -r requirements.txt
    ```

5.  **Place the Model**
    Ensure your folder structure looks like this:

    ```text
    MoNet-Analyzer/
    ├── models/
    │   └── FINALmodel_300.h5  <-- MUST BE HERE
    ├── main.py
    └── ...
    ```

-----

## 🚀 Usage Guide

The entire process is launched from the main GUI script.

### 1\. Launch the GUI

Make sure your `.venv` is active, then run:

```bash
python main.py
```

### 2\. Scan Inputs (Tab 1)

  * **Input Data Folder:** Browse to the folder containing your raw CSV trajectory files.
  * Click **SCAN FILES**. The tool will recursively find all `.csv` files, preserving the subfolder structure.

### 3\. Configure Filter (Tab 2)

Select the type of motion you wish to isolate:

  * **Keep All:** Saves all valid trajectories.
  * **Keep Brownian Only:** Normal diffusion (random motion).
  * **Keep FBM Only:** Fractional Brownian Motion (crowded/elastic environments).
  * **Keep CTRW Only:** Continuous Time Random Walk (trapping/hopping).

### 4\. Run Batch (Tab 3)

Click the **RUN BATCH ANALYSIS** button.

The application will:

1.  Load the Neural Network.
2.  Create a mirrored output folder named `MoNet_[InputFolderName]` next to your source folder.
3.  Process every file, filter the tracks, and save them.

The log will provide real-time feedback:

```text
🚀 Starting Batch Analysis...
🧠 Loading Model: FINALmodel_300.h5...
⏳ Processing sample_01.csv...
✅ sample_01.csv: 150 -> 42 tracks kept
⚠️ sample_02.csv: 0 Brownian tracks found. File Skipped.
🎉 --- Batch Complete ---
```

-----

## 📂 Project Structure

| File | Description |
| :--- | :--- |
| **`main.py`** | **Entry Point.** The GUI logic, logging system, and threading manager. |
| **`monet_engine.py`** | **The Brain.** Handles data loading, smart column detection, TensorFlow inference, and safe CSV writing. |
| **`models/`** | Directory for storing the trained `.h5` neural network file. |
| **`requirements.txt`** | Lists dependencies (`tensorflow`, `pandas`, `numpy`, etc.). |
| **`app_settings.json`** | Stores the last used input folder path for convenience. |