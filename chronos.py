import argparse
import os
import sys
import textwrap
from datetime import datetime, timedelta
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

# Try to import plotly for HTML generation
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    # Plotly will only be strictly required if the user chooses .html output
    pass


def load_project_data(file_path, date_mode="eu"):
    """Loads data from a CSV or Excel file and standardizes column names."""
    # IF FILE_PATH IS A TUPLE, EXTRACT THE FIRST ELEMENT
    if isinstance(file_path, tuple):
        file_path = file_path[0] if len(file_path) > 0 else ""

    file_path = str(file_path).strip()

    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' does not exist.")
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        else:
            print("Error: Unsupported file format. Please provide a .csv or .xlsx file.")
            sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    df.columns = [str(col).strip() for col in df.columns]

    required_cols = ["Task", "Target Date", "Duration", "Type"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Error: Missing required columns in the file: {missing_cols}. Expected format: {required_cols}")
        sys.exit(1)

    parsed_dates = []
    for idx, row in df.iterrows():
        raw_date = str(row["Target Date"]).strip()

        try:
            if date_mode == "us":
                clean_date = raw_date.replace("/", ".").replace("-", ".")
                parsed_d = datetime.strptime(clean_date, "%m.%d.%Y")
            elif date_mode == "iso":
                clean_date = raw_date.replace("/", "-").replace(".", "-")
                parsed_d = datetime.strptime(clean_date, "%Y-%m-%d")
            else:
                clean_date = raw_date.replace("/", ".").replace("-", ".")
                parsed_d = datetime.strptime(clean_date, "%d.%m.%Y")

            parsed_dates.append(parsed_d)
        except ValueError:
            print("\n" + "="*70)
            print(" STRICT DATE FORMAT VALIDATION ERROR ")
            print("="*70)
            print(f"Row {idx + 2}: Invalid date string encountered: '{raw_date}' for mode '{date_mode}'.")
            print("\nCRITICAL REQUIREMENT:")
            print(f"All dates must strictly match the selected numerical format (--date-format / -df):")
            print("  eu  -> DD.MM.YYYY, DD/MM/YYYY or DD-MM-YYYY (e.g., 21.03.2027) - DEFAULT")
            print("  us  -> MM.DD.YYYY, MM/DD/YYYY or MM-DD-YYYY (e.g., 03/21/2027)")
            print("  iso -> YYYY-MM-DD, YYYY/MM/DD or YYYY.MM.DD (e.g., 2027-03-21)")
            print("\nTEXTUAL MONTHS (like '15-Sep' or '08-Feb') ARE NOT ALLOWED.")
            print("Please fix the file data layout or pass the correct -df flag.")
            print("="*70 + "\n")
            sys.exit(1)

    df["End"] = parsed_dates
    return df

def get_start_date(row):
    """Calculates the start date based on the Duration string."""
    dur = str(row["Duration"]).strip()
    end = row["End"]
    if dur.endswith("w"):
        return end - timedelta(weeks=int(dur[:-1]))
    elif dur.endswith("d"):
        return end - timedelta(days=int(dur[:-1]))
    return end


def pack_tasks(dataframe):
    """Groups overlapping tasks into the minimum number of rows."""
    levels = []
    dataframe["Level"] = 0
    for idx, row in dataframe.iterrows():
        placed = False
        for lvl_idx, lvl_end_time in enumerate(levels):
            if row["Start"] >= lvl_end_time:
                levels[lvl_idx] = row["End"]
                dataframe.at[idx, "Level"] = lvl_idx
                placed = True
                break
        if not placed:
            levels.append(row["End"])
            dataframe.at[idx, "Level"] = len(levels) - 1
    return dataframe


def generate_png_timeline(df, unique_types, colors, args):
    """Generates the static high-quality PNG chart using Matplotlib."""
    df_normal = df[df["Type"] != "dependency"].copy()
    df_dep = df[df["Type"] == "dependency"].copy()

    if not df_normal.empty:
        df_normal = pack_tasks(df_normal)
    if not df_dep.empty:
        df_dep = pack_tasks(df_dep)

    # Vertical distribution spacing calculations
    df_normal["Y"] = 0.15 + df_normal["Level"] * 0.08
    df_dep["Y"] = -0.32 - df_dep["Level"] * 0.08

    fig, ax = plt.subplots(figsize=(26, 12), dpi=120)
    ax.axhline(0, color="black", linewidth=2.5, zorder=2)

    def draw_timeline_section(dataframe, is_above=True):
        dataframe = dataframe.sort_values(by="Start")

        # Layer 1: Horizontal duration bars
        for _, row in dataframe.iterrows():
            dur_days = (row["End"] - row["Start"]).days
            ax.barh(row["Y"], dur_days, left=row["Start"], height=0.04, color=colors[row["Type"]], edgecolor="black", alpha=0.9, zorder=3)

        # Layer 2: Connector lines (hidden behind text boxes)
        for i, (_, row) in enumerate(dataframe.iterrows()):
            dur_days = (row["End"] - row["Start"]).days
            task_color = colors[row["Type"]]
            mid_date = row["Start"] + timedelta(days=dur_days / 2)

            levels_count = dataframe["Level"].max() + 1
            if is_above:
                base_offset = 0.45 + (i % 4) * 0.55
                text_y = (0.15 + levels_count * 0.08) + base_offset
            else:
                base_offset = 0.55 + (i % 4) * 0.55
                text_y = (-0.32 - levels_count * 0.08) - base_offset

            ax.plot([mid_date, mid_date], [row["Y"], text_y], color=task_color, linewidth=0.8, alpha=0.4, zorder=1)

        # Layer 3: Text-wrapped colorful callout labels
        for i, (_, row) in enumerate(dataframe.iterrows()):
            dur_days = (row["End"] - row["Start"]).days
            task_color = colors[row["Type"]]
            mid_date = row["Start"] + timedelta(days=dur_days / 2)

            levels_count = dataframe["Level"].max() + 1
            if is_above:
                base_offset = 0.45 + (i % 4) * 0.55
                text_y = (0.15 + levels_count * 0.08) + base_offset
            else:
                base_offset = 0.55 + (i % 4) * 0.55
                text_y = (-0.32 - levels_count * 0.08) - base_offset

            text_color = "white" if row["Type"] in ["implementation", "bug fixing", "dependency", "holidays"] or colors[row["Type"]] in ["#1f77b4", "#9467bd", "#d62728", "#8c564b"] else "black"
            wrapped_text = textwrap.fill(str(row["Task"]), width=20)
            final_text = f"{wrapped_text}\n({row['Duration']})"

            ax.text(
                mid_date, text_y, final_text, fontsize=8, ha="center", va="center", color=text_color, weight="bold", zorder=5,
                bbox=dict(boxstyle="round,pad=0.4", fc=task_color, ec="black", lw=0.5, alpha=1.0, zorder=5)
            )

    if not df_normal.empty:
        draw_timeline_section(df_normal, is_above=True)
    if not df_dep.empty:
        draw_timeline_section(df_dep, is_above=False)

    norm_max = df_normal["Y"].max() if not df_normal.empty else 0.5
    dep_min = df_dep["Y"].min() if not df_dep.empty else -0.5
    max_y = norm_max + 2.8
    min_y = dep_min - 4.2
    ax.set_ylim(min_y, max_y)

    ax.xaxis.set_tick_params(labelbottom=False, bottom=False)

    # Calibrate bi-weekly ticks
    start_date = df["Start"].min()
    while start_date.weekday() != 0:
        start_date -= timedelta(days=1)
    end_date = df["End"].max() + timedelta(days=14)

    current_tick = start_date
    while current_tick <= end_date:
        ax.plot([current_tick, current_tick], [-0.05, 0.05], color="black", linewidth=2, zorder=3)
        ax.text(current_tick, -0.11, current_tick.strftime("%d-%b"), fontsize=9, weight="bold", color="black", ha="right", va="top", rotation=45, zorder=6)
        current_tick += timedelta(weeks=2)

    # Top calendar headers
    dates_range = pd.date_range(start=df["Start"].min() - timedelta(days=7), end=df["End"].max() + timedelta(days=14))
    first_days = dates_range[dates_range.is_month_start]

    for f_day in first_days:
        ax.plot([f_day, f_day], [min_y + 0.8, max_y - 0.5], color="lightgray", linestyle="--", linewidth=1, zorder=1)
        ax.text(f_day, max_y - 0.3, f_day.strftime("%b %Y"), fontsize=10, weight="bold", color="#2c3e50", ha="center", va="center", zorder=10,
                bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none", alpha=1.0))

    legend_elements = [plt.Rectangle((0, 0), 1, 1, facecolor=colors[t], edgecolor="black", alpha=0.9, label=str(t).title()) for t in unique_types]
    ax.legend(handles=legend_elements, loc="lower center", bbox_to_anchor=(0.5, 0.02), ncol=min(len(unique_types), 8), fontsize=10, frameon=True, facecolor="#f8f9fa", edgecolor="gray")

    ax.get_yaxis().set_visible(False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.title(args.title, fontsize=16, pad=40, weight="bold", color="#1a1a1a")
    plt.tight_layout()
    plt.savefig(args.output, bbox_inches="tight", dpi=120)


def generate_html_timeline(df, colors, args):
    """Generates an interactive HTML timeline that looks EXACTLY like the custom PNG version."""
    if "plotly" not in sys.modules:
        print("Error: The 'plotly' library is required for HTML output. Please run: pip install plotly")
        sys.exit(1)

    # 1. Process data structures (same logic as PNG)
    df_normal = df[df["Type"] != "dependency"].copy()
    df_dep = df[df["Type"] == "dependency"].copy()

    if not df_normal.empty:
        df_normal = pack_tasks(df_normal)
    if not df_dep.empty:
        df_dep = pack_tasks(df_dep)

    df_normal["Y"] = 0.15 + df_normal["Level"] * 0.08
    df_dep["Y"] = -0.32 - df_dep["Level"] * 0.08

    # Combine data to calculate dynamic axis bounds
    norm_max = df_normal["Y"].max() if not df_normal.empty else 0.5
    dep_min = df_dep["Y"].min() if not df_dep.empty else -0.5
    max_y = norm_max + 2.8
    min_y = dep_min - 4.2

    # Initialize layout figure
    fig = go.Figure()

    # 2. Draw Month-start vertical background grid lines
    dates_range = pd.date_range(start=df["Start"].min() - timedelta(days=7), end=df["End"].max() + timedelta(days=14))
    first_days = dates_range[dates_range.is_month_start]

    for f_day in first_days:
        # Vertical dotted line
        fig.add_trace(go.Scatter(
            x=[f_day, f_day], y=[min_y + 0.8, max_y - 0.5],
            mode="lines", line=dict(color="lightgray", width=1, dash="dash"),
            showlegend=False, hoverinfo="skip"
        ))
        # Month Label at the top
        fig.add_annotation(
            x=f_day, y=max_y - 0.3, text=f_day.strftime('%b %Y'),
            showarrow=False, font=dict(size=11, color="#2c3e50", weight="bold"),
            bgcolor="white", bordercolor="rgba(0,0,0,0)"
        )

    # 3. Draw central main timeline black axis line
    start_date = df["Start"].min()
    while start_date.weekday() != 0:
        start_date -= timedelta(days=1)
    end_date = df["End"].max() + timedelta(days=14)

    fig.add_trace(go.Scatter(
        x=[start_date, end_date], y=[0, 0],
        mode="lines", line=dict(color="black", width=3),
        showlegend=False, hoverinfo="skip"
    ))

    # Add bi-weekly timeline ticks and angled dates below the axis
    current_tick = start_date
    while current_tick <= end_date:
        fig.add_trace(go.Scatter(
            x=[current_tick, current_tick], y=[-0.05, 0.05],
            mode="lines", line=dict(color="black", width=2),
            showlegend=False, hoverinfo="skip"
        ))
        fig.add_annotation(
            x=current_tick, y=-0.11, text=current_tick.strftime('%d-%b'),
            showarrow=False, font=dict(size=10, color="black", weight="bold"),
            textangle=-45, xanchor="right", yanchor="top"
        )
        current_tick += timedelta(weeks=2)

    # 4. Helper drawing loop matching custom PNG layout layers
    def render_plotly_section(dataframe, is_above=True):
        dataframe = dataframe.sort_values(by="Start")
        added_legends = set()

        for i, (_, row) in enumerate(dataframe.iterrows()):
            dur_days = (row["End"] - row["Start"]).days
            task_color = colors[row["Type"]]
            mid_date = row["Start"] + timedelta(days=dur_days / 2)

            levels_count = dataframe["Level"].max() + 1
            if is_above:
                base_offset = 0.45 + (i % 4) * 0.55
                text_y = (0.15 + levels_count * 0.08) + base_offset
            else:
                base_offset = 0.55 + (i % 4) * 0.55
                text_y = (-0.32 - levels_count * 0.08) - base_offset

            # Determine text color contrast
            text_color = "white" if row["Type"] in ["implementation", "bug fixing", "dependency", "holidays"] or colors[row["Type"]] in ["#1f77b4", "#9467bd", "#d62728", "#8c564b"] else "black"
            
            # Text wrap for callout body formatting
            wrapped_text = "<br>".join(textwrap.wrap(str(row["Task"]), width=20))
            final_text = f"<b>{wrapped_text}</b><br>({row['Duration']})"
            
            # Configure custom hover tooltip structure
            hover_card = f"<b>Task:</b> {row['Task']}<br><b>Duration:</b> {row['Duration']}<br><b>Target:</b> {row['Target Date']}"

            # A. Draw connector thin line (Layer 2)
            fig.add_trace(go.Scatter(
                x=[mid_date, mid_date], y=[row["Y"], text_y],
                mode="lines", line=dict(color=task_color, width=1),
                opacity=0.4, showlegend=False, hoverinfo="skip"
            ))

            # B. Draw horizontal thickness bar (Layer 1)
            half_height = 0.02
            box_x = [row["Start"], row["End"], row["End"], row["Start"], row["Start"]]
            box_y = [row["Y"]-half_height, row["Y"]-half_height, row["Y"]+half_height, row["Y"]+half_height, row["Y"]-half_height]
            
            show_in_legend = False
            if row["Type"] not in added_legends:
                added_legends.add(row["Type"])
                show_in_legend = True

            fig.add_trace(go.Scatter(
                x=box_x, y=box_y, fill="toself", mode="lines", fillcolor=task_color,
                line=dict(color="black", width=1), opacity=0.9, name=str(row["Type"]).title(),
                legendgroup=str(row["Type"]), showlegend=show_in_legend, text=hover_card, hoverinfo="text",
                hoverlabel=dict(bgcolor=task_color, font=dict(color=text_color, weight="bold", size=11, family="Arial"))
            ))

            # C. Ukryta, niewidoczna tarcza hover dla dymka z wymuszonym stylem kolorystycznym okienka
            fig.add_trace(go.Scatter(
                x=[mid_date], y=[text_y],
                mode="markers",
                marker=dict(size=35, color="rgba(0,0,0,0)"),
                showlegend=False,
                legendgroup=str(row["Type"]),
                text=hover_card,
                hoverinfo="text",
                zorder=4,
                hoverlabel=dict(bgcolor=task_color, font=dict(color=text_color, weight="bold", size=11, family="Arial"))
            ))

            # D. Draw text Callout cloud container box (Layer 3)
            fig.add_annotation(
                x=mid_date, y=text_y, text=final_text,
                showarrow=False, align="center", font=dict(size=9, color=text_color),
                bordercolor="black", borderwidth=0.5, borderpad=5,
                bgcolor=task_color, opacity=1.0
            )

    # Render top/bottom sets matching layout targets
    if not df_normal.empty: render_plotly_section(df_normal, is_above=True)
    if not df_dep.empty: render_plotly_section(df_dep, is_above=False)

    # 5. Global chart canvas styling adjustments
    fig.update_layout(
        title=dict(text=f"<b>{args.title}</b>", x=0.5, y=0.96, font=dict(size=18, color="#1a1a1a")),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            type="date", range=[df["Start"].min() - timedelta(days=5), df["End"].max() + timedelta(days=10)],
            showgrid=False, zeroline=False, showticklabels=False
        ),
        yaxis=dict(range=[min_y, max_y], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        legend=dict(
            orientation="h", yanchor="bottom", y=0.01, xanchor="center", x=0.5,
            bgcolor="#f8f9fa", bordercolor="gray", borderwidth=1
        ),
        margin=dict(t=80, b=60, l=40, r=40),
        height=850
    )

    fig.write_html(args.output)


def main():
    help_epilog = ("DATE FORMAT LAYOUT REQUIRMENT:\n"
                   "  Set your regional formatting mode using the '--date-format' / '-df' parameter:\n"
                   "  -df eu  -> European / Indian layout style (DD.MM.YYYY) - [DEFAULT]\n"
                   "  -df us  -> American layout style (MM/DD/YYYY)\n"
                   "  -df iso -> Asian / International style (YYYY-MM-DD)")
    
    parser = argparse.ArgumentParser(
        description="Chronos CLI v1.1.0 - Highly optimized timeline generator supporting PNG and HTML output formats.",
        epilog=help_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-f", "--file", required=True,
        help="Path or name of the input CSV or Excel data file (e.g., project_data.xlsx).",
    )
    parser.add_argument(
        "-t", "--title", required=True,
        help="The main title text displayed at the top of the timeline chart.",
    )
    parser.add_argument(
        "-o", "--output", required=False, default="project_timeline_output.png",
        help="Optional: Output file path. Use '.png' extension for image or '.html' for interactive view.\nDefaults to 'project_timeline_output.png'."
    )
    parser.add_argument(
        "-df", "--date-format", required=False, default="eu",
        choices=["us", "eu", "iso"],
        help="Optional: Date format processing mode for international teams.\n"
             "  eu    : Enforce European/Indian format (DD/MM/YYYY) - DEFAULT\n"
             "  us    : Enforce US format (MM/DD/YYYY)\n"
             "  iso   : Enforce Asian/Standard format (YYYY/MM/DD)"
    )

    args = parser.parse_args()

    file_str = str(args.file).replace("(", "").replace(")", "").replace("'", "").replace('"', "").strip()
    if file_str.endswith(","): file_str = file_str[:-1].strip()

    title_str = str(args.title).replace("(", "").replace(")", "").replace("'", "").replace('"', "").strip()
    if title_str.endswith(","): title_str = title_str[:-1].strip()

    output_str = str(args.output).replace("(", "").replace(")", "").replace("'", "").replace('"', "").strip()
    if output_str.endswith(","): output_str = output_str[:-1].strip()

    date_mode = str(args.date_format).replace("(", "").replace(")", "").replace("'", "").replace('"', "").strip()
    if date_mode.endswith(","): date_mode = date_mode[:-1].strip()

    output_ext = os.path.splitext(output_str)[1].lower()
    
    if output_ext not in [".png", ".html"]:
        print("Error: Invalid output file extension. Only '.png' and '.html' are supported.")
        sys.exit(1)

    # Load data using the cleaned file path string
    df = load_project_data(file_str, date_mode=date_mode)
    df["Start"] = df.apply(get_start_date, axis=1)
    df = df.sort_values(by="Start").reset_index(drop=True)

    colors = {
        "implementation": "#1f77b4", "testing": "#ff7f0e", "reporting": "#2ca02c",
        "bug fixing": "#d62728", "dependency": "#9467bd", "holidays": "#8c564b",
        "certification": "#e377c2", "monthly release": "#bcbd22",
    }

    unique_types = df["Type"].unique()
    used_hex_colors = set(colors.values())
    available_fallback_colors = [
        mcolors.to_hex(c) for c in plt.cm.tab20.colors
        if mcolors.to_hex(c) not in used_hex_colors
    ]

    color_idx = 0
    for t in unique_types:
        if t not in colors:
            colors[t] = available_fallback_colors[color_idx % len(available_fallback_colors)]
            color_idx += 1

    # Overwrite args object values with safe string types for backend engine consumption
    args.file = file_str
    args.title = title_str
    args.output = output_str

    if output_ext == ".png":
        generate_png_timeline(df, unique_types, colors, args)
    elif output_ext == ".html":
        generate_html_timeline(df, colors, args)

    print(f"Success! Chronos CLI generated and saved your timeline asset as '{output_str}'.")


if __name__ == "__main__":
    main()
