# Chronos CLI (v1.3.0)

Chronos CLI is a highly optimized, production-ready pipeline timeline data asset generator. It enables engineering and product teams to dynamically render raw roadmap inputs (from Excel or CSV exports) into beautiful, standard-compliant visualizations.

The tool provides an architectural separation of concerns by shipping dual rendering engines:

* **Static Layer (PNG):** A high-definition, text-wrapped vector presentation designed for status documents, newsletters, and PDF reporting.
* **Interactive Layer (HTML):** A modern, responsive, and vector-based web preview tool leveraging standard browser mechanics to embed independent, cross-linked platform hooks into the roadmap interface.

---

## Key Features

* **Multi-Format Generation:** Automate your presentation cycle by exporting plots directly to `.png` layout formats or `.html` preview components.
* **Robust International Date Support:** Built-in numerical regional safeguards (`-df eu`, `-df us`, `-df iso`) prevent multi-regional scheduling confusion and mismatch traps across global timezones.
* **Smart Overlap Protection:** Automatic visual multi-lane layout packing packs parallel tasks into optimized rows without horizontal collision.
* **Multi-Link Ecosystem Integration:** Embed optional independent hyperlink buttons (`[Jira]` & `[Conf]`) directly inside interactive web elements without breaking static layout compatibility.
* **Production Validation System:** Deep dataset structure tracking captures structural data row errors and syntax formatting issues before compiling outputs.
* **PEP 8 & Type-Safe Integrity:** Fully refactored codebase optimized for clean static syntax processing with strict zero-warning Mypy/Pylance policies.

---

## Project Directory Layout

The workspace implements a strict Separation of Concerns (SoC) model separating core business data routing from graphics presentation engines:

```text
timeline/
│
├── chronos.py             # Main entry point (CLI Parser & Flow Router)
├── requirements.txt       # Frozen production dependencies list
├── README.md              # Project onboarding documentation
│
└── src/                   # Core modular package modules
    ├── __init__.py        # Python package initialization safe-hook
    ├── data_loader.py     # Data validation, column binding & date parsing engine
    ├── png_generator.py   # HD Static rendering pipeline (Matplotlib engine)
    └── html_generator.py  # Sticky interactive web pipeline (Plotly components engine)
```

---

## Installation & Setup

1. **Clone the Repository:**

   ```bash
   git clone https://github.com
   cd timeline
   ```

2. **Initialize a Local Virtual Environment (`venv`):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Frozen Production Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

---

## Data Input Requirements

Your source `.csv` or `.xlsx` spreadsheet must contain the following required structural column headings:

| Column Header | Requirement | Accepted Formats / Examples |
| :--- | :--- | :--- |
| **Task** | Required | Any task summary text string |
| **Target Date** | Required | Numerical representation depending on the chosen `-df` mode |
| **Duration** | Required | `[Value][Unit]` schema where units are weeks (`w`) or days (`d`) (e.g., `3w`, `5d`) |
| **Type** | Required | Mapping type key for dynamic color binding (e.g., `implementation`, `dependency`, `testing`) |
| **Jira Link** | Optional | Full URL connection string to an explicit ticket (e.g., `https://example-jira.com`) |
| **Confluence Link** | Optional | Full URL connection string to a documentation hub (e.g., `https://example-confluence.com`) |
| **Connections** | Optional | `;` separated group keys (e.g., `auth-epic;q3-release`). Tasks sharing a key highlight together on click in HTML output. Leave blank for a standalone task. |

---

## Usage Guide

Run the main steering script from your command line interface. The compilation target is evaluated automatically based on the extension of your output file (`-o`).

### 1. Generate high-definition static plots (PNG)

```bash
python3 chronos.py -f template.xlsx -t "Core Implementation Timeline" -o roadmap.png
```

### 2. Generate interactive web roadmaps with Jira/Confluence hooks (HTML)

```bash
python3 chronos.py -f template.xlsx -t "Interactive Platform Status" -o preview.html
```

### 3. Handle multi-regional global file formats (`-df` / `--date-format`)

Enforce explicit regional calculation boundaries to prevent dates from being shifted on a cross-regional basis:

```bash
# Process standard European datasets (DD.MM.YYYY) [DEFAULT]
python3 chronos.py -f template.xlsx -t "EU Roadmap" -df eu

# Process American datasets (MM/DD/YYYY)
python3 chronos.py -f template.xlsx -t "US Roadmap" -df us

# Process Asian / Standard international datasets (YYYY-MM-DD)
python3 chronos.py -f template.xlsx -t "Global Roadmap" -df iso
```

### 4. Display help dashboard

```bash
python3 chronos.py --help
```

---

## Architecture Context

Chronos CLI adheres to the following core software design concepts:

* **Single Responsibility Principle (SRP):** Each application block retains a singular scope boundary. Data pipeline parsing (`data_loader`) is isolated from graphics compiling routines (`png_generator` / `html_generator`).
* **Loose Coupling:** The interactive component interface does not depend on Matplotlib layout spaces. This design ensures that subsequent module expansions (e.g., automated third-party chat platform ecosystem notifications) can be attached smoothly without regression.
