import textwrap
from datetime import timedelta
import matplotlib.dates as mdates  # type: ignore[import-untyped]
import matplotlib.patches as mpatches
import matplotlib.patheffects as mpe
import matplotlib.pyplot as plt


# Matches the HTML theme's raised look.
_LIFT = [
    mpe.withSimplePatchShadow(
        offset=(1.8, -1.8), shadow_rgbFace="black", alpha=0.35
    )
]


def _pack_tasks(dataframe):
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


# Vertical spacing constants for stacking callout label rows above/below
# the axis; must match the offsets used when rendering each label.
_LABEL_BASE_ABOVE = 0.45
_LABEL_BASE_BELOW = 0.55
_LABEL_STEP = 0.55
_LABEL_PAD_ABOVE = 0.7
_LABEL_PAD_BELOW = 2.0

# Figure width in px (figsize width * dpi, must match plt.subplots below)
# and the estimated rendered width of a wrapped callout box, used to size
# the label row gap in day-units so boxes on the same row never touch.
_PLOT_WIDTH_PX = 26 * 120
_LABEL_BOX_PX = 170


def _estimate_label_gap_days(df, plot_width_px=_PLOT_WIDTH_PX):
    """Estimates the day-gap two labels need to not overlap when plotted."""
    total_span_days = max((df["End"].max() - df["Start"].min()).days, 1) + 20
    return max(3, _LABEL_BOX_PX * total_span_days / plot_width_px)


def _pack_labels(dataframe, min_gap_days):
    """Assigns each task a label row so nearby labels don't overlap."""
    mids = dataframe["Start"] + (dataframe["End"] - dataframe["Start"]) / 2
    row_last_mid = []
    label_row_by_index = {}
    for idx in mids.sort_values().index:
        mid = mids[idx]
        placed = False
        for row_idx, last_mid in enumerate(row_last_mid):
            if (mid - last_mid).days >= min_gap_days:
                row_last_mid[row_idx] = mid
                label_row_by_index[idx] = row_idx
                placed = True
                break
        if not placed:
            row_last_mid.append(mid)
            label_row_by_index[idx] = len(row_last_mid) - 1
    dataframe = dataframe.copy()
    dataframe["LabelRow"] = dataframe.index.map(label_row_by_index)
    return dataframe


def generate_png_timeline(df, unique_types, colors, args):
    """Generates the static high-quality PNG chart using Matplotlib."""
    df_normal = df[df["Type"] != "dependency"].copy()
    df_dep = df[df["Type"] == "dependency"].copy()

    min_gap_days = _estimate_label_gap_days(df)
    if not df_normal.empty:
        df_normal = _pack_tasks(df_normal)
        df_normal = _pack_labels(df_normal, min_gap_days)
    if not df_dep.empty:
        df_dep = _pack_tasks(df_dep)
        df_dep = _pack_labels(df_dep, min_gap_days)

    # Vertical distribution spacing calculations
    if not df_normal.empty:
        df_normal["Y"] = 0.15 + df_normal["Level"] * 0.08
    if not df_dep.empty:
        df_dep["Y"] = -0.32 - df_dep["Level"] * 0.08

    fig, ax = plt.subplots(figsize=(26, 12), dpi=120)
    ax.axhline(0, color="black", linewidth=2.5, zorder=2)

    def draw_timeline_section(dataframe, is_above=True):
        dataframe = dataframe.sort_values(by="Start")

        # Layer 1: Horizontal duration bars
        for _, row in dataframe.iterrows():
            dur_days = (row["End"] - row["Start"]).days
            start_num = float(mdates.date2num(row["Start"]))
            bars = ax.barh(
                row["Y"], dur_days, left=start_num, height=0.04,
                color=colors[row["Type"]], edgecolor="black", alpha=0.9,
                zorder=3
            )
            for patch in bars.patches:
                patch.set_path_effects(_LIFT)

        # Layer 2: Connector lines (hidden behind text boxes)
        for _, row in dataframe.iterrows():
            dur_days = (row["End"] - row["Start"]).days
            task_color = colors[row["Type"]]
            mid_date = row["Start"] + timedelta(days=dur_days / 2)
            mid_date_num = float(mdates.date2num(mid_date))

            levels_count = dataframe["Level"].max() + 1
            if is_above:
                base_offset = _LABEL_BASE_ABOVE + row["LabelRow"] * _LABEL_STEP
                text_y = (0.15 + levels_count * 0.08) + base_offset
            else:
                base_offset = _LABEL_BASE_BELOW + row["LabelRow"] * _LABEL_STEP
                text_y = (-0.32 - levels_count * 0.08) - base_offset

            ax.plot(
                [mid_date_num, mid_date_num], [row["Y"], text_y],
                color=task_color, linewidth=0.8, alpha=0.4, zorder=1
            )

        # Layer 3: Text-wrapped colorful callout labels
        for _, row in dataframe.iterrows():
            dur_days = (row["End"] - row["Start"]).days
            task_color = colors[row["Type"]]
            mid_date = row["Start"] + timedelta(days=dur_days / 2)
            mid_date_num = float(mdates.date2num(mid_date))

            levels_count = dataframe["Level"].max() + 1
            if is_above:
                base_offset = _LABEL_BASE_ABOVE + row["LabelRow"] * _LABEL_STEP
                text_y = (0.15 + levels_count * 0.08) + base_offset
            else:
                base_offset = _LABEL_BASE_BELOW + row["LabelRow"] * _LABEL_STEP
                text_y = (-0.32 - levels_count * 0.08) - base_offset

            if row["Type"] in [
                "implementation", "bug fixing", "dependency", "holidays"
            ] or colors[row["Type"]] in [
                "#1f77b4", "#9467bd", "#d62728", "#8c564b"
            ]:
                text_color = "white"
            else:
                text_color = "black"

            wrapped_text = textwrap.fill(str(row["Task"]), width=20)
            final_text = f"{wrapped_text}\n({row['Duration']})"

            ax.text(
                mid_date_num, text_y, final_text, fontsize=8, ha="center",
                va="center", color=text_color, weight="bold", zorder=5,
                bbox=dict(
                    boxstyle="round,pad=0.4", fc=task_color,
                    ec="black", lw=0.5, alpha=1.0, zorder=5,
                    path_effects=_LIFT
                )
            )

    if not df_normal.empty:
        draw_timeline_section(df_normal, is_above=True)
    if not df_dep.empty:
        draw_timeline_section(df_dep, is_above=False)

    norm_max = df_normal["Y"].max() if not df_normal.empty else 0.5
    dep_min = df_dep["Y"].min() if not df_dep.empty else -0.5
    norm_label_rows = (
        df_normal["LabelRow"].max() + 1 if not df_normal.empty else 4
    )
    dep_label_rows = df_dep["LabelRow"].max() + 1 if not df_dep.empty else 4
    max_y = (
        norm_max + _LABEL_BASE_ABOVE
        + (norm_label_rows - 1) * _LABEL_STEP + _LABEL_PAD_ABOVE
    )
    min_y = (
        dep_min - _LABEL_BASE_BELOW
        - (dep_label_rows - 1) * _LABEL_STEP - _LABEL_PAD_BELOW
    )
    ax.set_ylim(min_y, max_y)

    ax.xaxis.set_tick_params(labelbottom=False, bottom=False)

    # Calibrate bi-weekly ticks
    start_date = df["Start"].min()
    while start_date.weekday() != 0:
        start_date -= timedelta(days=1)
    end_date = df["End"].max() + timedelta(days=14)

    current_tick = start_date
    while current_tick <= end_date:
        tick_num = float(mdates.date2num(current_tick))
        ax.plot(
            [tick_num, tick_num], [-0.05, 0.05],
            color="black", linewidth=2, zorder=3
        )
        ax.text(
            tick_num, -0.11, current_tick.strftime("%d-%b"),
            fontsize=9, weight="bold", color="black", ha="right",
            va="top", rotation=45, zorder=6
        )
        current_tick += timedelta(weeks=2)

    # Top calendar headers
    import pandas as pd  # type: ignore[import-untyped]
    dates_range = pd.date_range(
        start=df["Start"].min() - timedelta(days=7),
        end=df["End"].max() + timedelta(days=14)
    )
    first_days = dates_range[dates_range.is_month_start]

    for f_day in first_days:
        f_day_num = float(mdates.date2num(f_day))
        ax.plot(
            [f_day_num, f_day_num], [min_y + 0.8, max_y - 0.5],
            color="lightgray", linestyle="--", linewidth=1, zorder=1
        )
        ax.text(
            f_day_num, max_y - 0.3, f_day.strftime("%b %Y"), fontsize=10,
            weight="bold", color="#2c3e50", ha="center", va="center",
            zorder=10, bbox=dict(
                boxstyle="square,pad=0.2", fc="white", ec="none", alpha=1.0
            )
        )

    legend_elements = [
        mpatches.Rectangle(
            (0, 0), 1, 1, facecolor=colors[type_str], edgecolor="black",
            alpha=0.9, label=str(type_str).title()
        ) for type_str in unique_types
    ]
    ax.legend(
        handles=legend_elements, loc="lower center",
        bbox_to_anchor=(0.5, 0.02), ncol=min(len(unique_types), 8),
        fontsize=10, frameon=True, facecolor="#f8f9fa", edgecolor="gray"
    )

    ax.get_yaxis().set_visible(False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.title(args.title, fontsize=16, pad=40, weight="bold", color="#1a1a1a")

    # Add attribution in bottom right corner
    repo_url = "github.com/kkborowski/chronos-cli"
    ax.text(
        0.99, 0.01, f"Made with ❤️ using {repo_url}",
        transform=ax.transAxes, fontsize=10, color="#999999",
        ha="right", va="bottom", alpha=0.6
    )

    plt.tight_layout()
    plt.savefig(args.output, bbox_inches="tight", dpi=120)
