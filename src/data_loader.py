import os
import sys
from datetime import datetime, timedelta
from typing import Any, List
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd  # type: ignore[import-untyped]


class DataLoader:
    """Handles parsing, validation and stabilization of input timeline source
    data."""

    def __init__(self, file_path: Any, date_mode: str = "eu") -> None:
        self.file_path = self._clean_path(file_path)
        self.date_mode = date_mode
        self.unique_types: List[str] = []
        self.colors: dict[str, str] = {
            "implementation": "#1f77b4",
            "testing": "#ff7f0e",
            "reporting": "#2ca02c",
            "bug fixing": "#d62728",
            "dependency": "#9467bd",
            "holidays": "#8c564b",
            "certification": "#e377c2",
            "monthly release": "#bcbd22",
        }

    def _clean_path(self, path_input: Any) -> str:
        """Safely untangles tuple artifacts and extracts clean file path
        string."""
        if isinstance(path_input, tuple):
            path_input = path_input[0] if len(path_input) > 0 else ""
        return str(path_input).strip()

    def get_clean_data(self) -> pd.DataFrame:
        """Loads and runs multi-regional numerical date format validation
        schemas."""
        if not os.path.exists(self.file_path):
            print(f"Error: The file '{self.file_path}' does not exist.")
            sys.exit(1)

        ext = os.path.splitext(self.file_path)[1].lower()
        try:
            if ext == ".csv":
                df = pd.read_csv(self.file_path)
            elif ext in [".xlsx", ".xls"]:
                df = pd.read_excel(self.file_path)
            else:
                print(
                    "Error: Unsupported file format. Please provide a .csv or "
                    ".xlsx file."
                            )
                sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)

        df.columns = [str(col).strip() for col in df.columns]

        required_cols = ["Task", "Target Date", "Duration", "Type"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(
                f"Error: Missing required columns in the file: {missing_cols}."
                f" Expected format: {required_cols}"
            )
            sys.exit(1)

        # Secure optional link layout schema configurations safely
        for col_name in [
            "Jira Link", "Confluence Link", "Connections", "Description"
        ]:
            if col_name not in df.columns:
                df[col_name] = ""
            else:
                df[col_name] = df[col_name].fillna("").astype(str).str.strip()

        if "Placement" not in df.columns:
            df["Placement"] = ""
        else:
            df["Placement"] = (
                df["Placement"].fillna("").astype(str).str.strip().str.lower()
            )

        parsed_dates = []
        for idx, row in df.iterrows():
            raw_value = row["Target Date"]
            row_idx = int(str(idx))

            # Excel date-formatted cells arrive as real datetime objects;
            # use them directly instead of running strict string parsing.
            if isinstance(raw_value, pd.Timestamp):
                parsed_dates.append(raw_value.to_pydatetime())
                continue
            if isinstance(raw_value, datetime):
                parsed_dates.append(raw_value)
                continue

            raw_date = str(raw_value).strip()

            try:
                if self.date_mode == "us":
                    clean_date = raw_date.replace("/", ".").replace("-", ".")
                    parsed_d = datetime.strptime(clean_date, "%m.%d.%Y")
                elif self.date_mode == "iso":
                    clean_date = raw_date.replace("/", "-").replace(".", "-")
                    parsed_d = datetime.strptime(clean_date, "%Y-%m-%d")
                else:
                    clean_date = raw_date.replace("/", ".").replace("-", ".")
                    parsed_d = datetime.strptime(clean_date, "%d.%m.%Y")
                parsed_dates.append(parsed_d)
            except ValueError:
                print("\n" + "=" * 70)
                print(" STRICT DATE FORMAT VALIDATION ERROR ")
                print("=" * 70)
                print(
                    f"Row {row_idx + 2}: Invalid date string: '{raw_date}' "
                    f"for mode '{self.date_mode}'."
                )
                print("\nCRITICAL REQUIREMENT:")
                print("All dates must strictly match the selected format:")
                print(
                    "  eu  -> DD.MM.YYYY, DD/MM/YYYY or DD-MM-YYYY - DEFAULT"
                    )
                print("  us  -> MM.DD.YYYY, MM/DD/YYYY or MM-DD-YYYY")
                print("  iso -> YYYY-MM-DD, YYYY/MM/DD or YYYY.MM.DD\n")
                print(
                    "TEXTUAL MONTHS (like '15-Sep' or '08-Feb') ARE FORBIDDEN."
                    )
                print(
                    "Please fix the file data layout or pass the correct flag."
                    )
                print("=" * 70 + "\n")
                sys.exit(1)

        df["End"] = parsed_dates
        df["Start"] = df.apply(self._calculate_start_date, axis=1)
        df = df.sort_values(by="Start").reset_index(drop=True)
        df["IsAbove"] = df.apply(self._resolve_placement, axis=1)

        self._resolve_dynamic_colors(df)
        return df

    def _resolve_placement(self, row: Any) -> bool:
        """Applies the 'Placement' override, else falls back to Type-based
        default (dependency tasks go below, everything else goes above)."""
        placement = str(row["Placement"]).strip().lower()
        if placement == "up":
            return True
        if placement == "down":
            return False
        return str(row["Type"]).strip().lower() != "dependency"

    def _calculate_start_date(self, row: Any) -> datetime:
        """Calculates start datetime boundary based on duration parameters."""
        dur = str(row["Duration"]).strip()
        end = row["End"]
        if dur.endswith("w"):
            return end - timedelta(weeks=int(dur[:-1]))
        elif dur.endswith("d"):
            return end - timedelta(days=int(dur[:-1]))
        return end

    def _resolve_dynamic_colors(self, df: pd.DataFrame) -> None:
        """Resolves fallback color configurations using official colormap
        syntax."""
        self.unique_types = [str(t) for t in df["Type"].unique()]
        used_hex_colors = set(self.colors.values())

        cmap = plt.get_cmap("tab20")
        available_fallback_colors = [
            mcolors.to_hex(cmap(i)) for i in range(20)
            if mcolors.to_hex(cmap(i)) not in used_hex_colors
        ]

        color_idx = 0
        for t in self.unique_types:
            if t not in self.colors:
                self.colors[t] = available_fallback_colors[
                    color_idx % len(available_fallback_colors)
                ]
                color_idx += 1
