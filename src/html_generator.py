import html
import sys
import textwrap
from datetime import timedelta
from typing import Any
import pandas as pd  # type: ignore[import-untyped]

go: Any = None
try:
    import plotly.graph_objects as go  # type: ignore[import-untyped,no-redef]
except ImportError:
    go = None


# Injected into the exported HTML: clicking a task highlights it plus every
# task sharing a Connections key, and dims the rest. Click the same task
# again (or double-click) to reset.
_HIGHLIGHT_JS = """
(function () {
    var gd = document.getElementById('{plot_id}');
    if (!gd) { return; }

    var DIM = 0.12;
    var selected = null;

    function sharesGroup(a, b) {
        if (!a || !b) { return false; }
        for (var i = 0; i < a.length; i++) {
            if (b.indexOf(a[i]) !== -1) { return true; }
        }
        return false;
    }

    function linkedIds(taskId, groups) {
        var ids = {};
        ids[taskId] = true;
        (gd.data || []).forEach(function (trace) {
            var meta = trace.meta;
            if (!meta || meta.taskId === undefined) { return; }
            if (sharesGroup(groups, meta.groups)) { ids[meta.taskId] = true; }
        });
        return ids;
    }

    function applyHighlight(ids) {
        var indices = [];
        var opacities = [];
        (gd.data || []).forEach(function (trace, i) {
            var meta = trace.meta;
            if (!meta || meta.taskId === undefined) { return; }
            var base = meta.baseOpacity === undefined ? 1 : meta.baseOpacity;
            var on = (ids === null) || (ids[meta.taskId] === true);
            indices.push(i);
            opacities.push(on ? base : base * DIM);
        });
        if (indices.length) {
            Plotly.restyle(gd, {opacity: opacities}, indices);
        }

        var update = {};
        (gd.layout.annotations || []).forEach(function (ann, i) {
            if (!ann.name || ann.name.indexOf('task-') !== 0) { return; }
            var id = ann.name.slice(5);
            var on = (ids === null) || (ids[id] === true);
            update['annotations[' + i + '].opacity'] = on ? 1 : DIM;
        });
        if (Object.keys(update).length) {
            Plotly.relayout(gd, update);
        }
    }

    var pointClicked = false;

    gd.on('plotly_click', function (ev) {
        if (!ev || !ev.points || !ev.points.length) { return; }
        var meta = ev.points[0].data.meta;
        if (!meta || meta.taskId === undefined) { return; }
        pointClicked = true;
        if (selected === meta.taskId) {
            selected = null;
            applyHighlight(null);
            return;
        }
        selected = meta.taskId;
        applyHighlight(linkedIds(meta.taskId, meta.groups));
    });

    // Runs after plotly_click, so a bare background click clears the state.
    gd.addEventListener('click', function (ev) {
        if (ev.target.closest && ev.target.closest('.modebar')) { return; }
        setTimeout(function () {
            if (!pointClicked && selected !== null) {
                selected = null;
                applyHighlight(null);
            }
            pointClicked = false;
        }, 0);
    });

    gd.on('plotly_doubleclick', function () {
        selected = null;
        applyHighlight(null);
    });
})();
"""


# Resolved in the browser on every page load, so the arrow tracks the
# viewer's current date rather than the date the file was generated.
_TODAY_JS = """
(function () {
    var gd = document.getElementById('{plot_id}');
    if (!gd) { return; }

    function pad(n) { return (n < 10 ? '0' : '') + n; }

    var now = new Date();
    var midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var iso = midnight.getFullYear() + '-' +
        pad(midnight.getMonth() + 1) + '-' + pad(midnight.getDate());

    var range = gd.layout.xaxis && gd.layout.xaxis.range;
    if (range) {
        var stamp = midnight.getTime();
        if (stamp < new Date(range[0]).getTime()) { return; }
        if (stamp > new Date(range[1]).getTime()) { return; }
    }

    Plotly.addTraces(gd, {
        x: [iso],
        y: [-0.12],
        mode: 'markers',
        marker: {symbol: 'triangle-up', size: 13, color: 'red'},
        showlegend: false,
        hoverinfo: 'text',
        text: 'Today: ' + midnight.toDateString(),
        cliponaxis: false,
        zorder: 5
    });
})();
"""


# Plotly's native hover label is not interactive, so task hovers use this
# custom card instead: it survives long enough to move onto it and click.
_TOOLTIP_JS = """
(function () {
    var gd = document.getElementById('{plot_id}');
    if (!gd) { return; }

    var tip = document.createElement('div');
    tip.style.cssText = [
        'position:absolute', 'display:none', 'z-index:1000',
        'max-width:340px', 'padding:8px 10px', 'border-radius:4px',
        'border:1px solid rgba(0,0,0,0.45)',
        'font:bold 11px Arial, sans-serif', 'line-height:1.4',
        'pointer-events:auto', 'box-shadow:0 2px 6px rgba(0,0,0,0.35)'
    ].join(';');
    if (getComputedStyle(gd).position === 'static') {
        gd.style.position = 'relative';
    }
    gd.appendChild(tip);

    var hideTimer = null;

    function hide() { tip.style.display = 'none'; }
    function cancelHide() {
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    }
    function scheduleHide() {
        cancelHide();
        hideTimer = setTimeout(hide, 350);
    }

    tip.addEventListener('mouseenter', cancelHide);
    tip.addEventListener('mouseleave', hide);

    function link(url, label, color) {
        return '<a href="' + url + '" target="_blank" ' +
            'rel="noopener noreferrer" style="color:' + color +
            ';text-decoration:underline;">' + label + '</a>';
    }

    function anchorPoint(pt, ev) {
        var size = gd._fullLayout && gd._fullLayout._size;
        if (size && pt.xaxis && pt.yaxis) {
            return {
                x: pt.xaxis.d2p(pt.x) + size.l,
                y: pt.yaxis.d2p(pt.y) + size.t
            };
        }
        var rect = gd.getBoundingClientRect();
        return {
            x: ev.event ? ev.event.clientX - rect.left : 0,
            y: ev.event ? ev.event.clientY - rect.top : 0
        };
    }

    gd.on('plotly_hover', function (ev) {
        var pt = ev.points && ev.points[0];
        if (!pt) { return; }
        var meta = pt.data.meta;
        if (!meta || meta.taskId === undefined) { return; }
        cancelHide();

        var links = [];
        if (meta.jira) { links.push(link(meta.jira, '[Jira]', meta.fg)); }
        if (meta.conf) { links.push(link(meta.conf, '[Conf]', meta.fg)); }

        tip.innerHTML = (pt.data.text || '') +
            (links.length ? '<br><br>' + links.join(' &nbsp; ') : '');
        tip.style.background = meta.bg;
        tip.style.color = meta.fg;
        tip.style.display = 'block';

        // Anchored to the task itself, not the cursor, so the gap is fixed.
        var GAP = 12;
        var at = anchorPoint(pt, ev);
        var w = tip.offsetWidth;
        var h = tip.offsetHeight;
        var x = at.x + GAP;
        var y = at.y + GAP;
        if (x + w > gd.clientWidth) { x = at.x - GAP - w; }
        if (y + h > gd.clientHeight) { y = at.y - GAP - h; }
        tip.style.left = Math.max(0, x) + 'px';
        tip.style.top = Math.max(0, y) + 'px';
    });

    gd.on('plotly_unhover', scheduleHide);
})();
"""


# Caps how wide a hover tooltip can grow, in characters per line.
_HOVER_WRAP_WIDTH = 60


def _format_description(raw):
    """Escapes and hard-wraps a description into hover tooltip lines."""
    text = " ".join(str(raw).split())
    if not text:
        return ""
    return "<br>".join(
        html.escape(line)
        for line in textwrap.wrap(text, width=_HOVER_WRAP_WIDTH)
    )


def _safe_url(raw):
    """Allows only http(s) links so sheet data cannot inject javascript: URLs."""
    url = str(raw).strip()
    if url.lower().startswith(("http://", "https://")):
        return url
    return ""


def _parse_connections(raw):
    """Splits a ';' separated Connections cell into normalized group keys."""
    tokens = str(raw).split(";")
    groups = []
    for token in tokens:
        key = token.strip().lower()
        if key and key not in groups:
            groups.append(key)
    return groups


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


def generate_html_timeline(df, colors, args):
    """Generates an interactive HTML timeline with clickable web shortcuts."""
    if go is None:
        print(
            "Error: 'plotly' is required for HTML output. "
            "Run: pip install plotly"
            )
        sys.exit(1)

    # 1. Process data structures (same logic as PNG)
    df_normal = df[df["Type"] != "dependency"].copy()
    df_dep = df[df["Type"] == "dependency"].copy()

    if not df_normal.empty:
        df_normal = _pack_tasks(df_normal)
    if not df_dep.empty:
        df_dep = _pack_tasks(df_dep)

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
    dates_range = pd.date_range(
        start=df["Start"].min() - timedelta(days=7),
        end=df["End"].max() + timedelta(days=14)
    )
    first_days = dates_range[dates_range.is_month_start]

    for f_day in first_days:
        fig.add_trace(go.Scatter(
            x=[f_day, f_day], y=[min_y + 0.8, max_y - 0.5],
            mode="lines", line=dict(color="lightgray", width=1, dash="dash"),
            showlegend=False, hoverinfo="skip"
        ))
        fig.add_annotation(
            x=f_day, y=max_y - 0.3, text=f_day.strftime('%b %Y'),
            showarrow=False, font=dict(
                size=11, color="#2c3e50", weight="bold"
            ), bgcolor="white", bordercolor="rgba(0,0,0,0)"
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
    task_id_counter = [0]

    def render_plotly_section(dataframe, is_above=True):
        dataframe = dataframe.sort_values(by="Start")
        added_legends = set()

        for i, (_, row) in enumerate(dataframe.iterrows()):
            task_id = task_id_counter[0]
            task_id_counter[0] += 1
            connections = _parse_connections(row.get("Connections", ""))
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
            if row["Type"] in [
                "implementation", "bug fixing", "dependency", "holidays"
            ] or colors[row["Type"]] in [
                "#1f77b4", "#9467bd", "#d62728", "#8c564b"
            ]:
                text_color = "white"
            else:
                text_color = "black"

            jira_url = _safe_url(row["Jira Link"])
            conf_url = _safe_url(row["Confluence Link"])

            wrapped_text = "<br>".join(
                textwrap.wrap(str(row["Task"]), width=20)
            )

            display_text = (
                f"<span style='pointer-events: none;'><b>"
                f"{wrapped_text}</b><br>"
                f"({row['Duration']})</span>"
            )

            links_html = []
            if jira_url:
                links_html.append(
                    f"<a href='{jira_url}' target='_blank' "
                    f"style='color:{text_color}; "
                    f"text-decoration:underline; font-weight:bold; "
                    f"pointer-events: auto;'>[Jira]</a>"
                )
            if conf_url:
                links_html.append(
                    f"<a href='{conf_url}' target='_blank' "
                    f"style='color:{text_color}; text-decoration:underline; "
                    f"font-weight:bold; pointer-events: auto;'>[Conf]</a>"
                )

            if links_html:
                display_text += (
                    f"<br><span style='pointer-events: auto;'> &nbsp; "
                    f"{' '.join(links_html)}</span>"
                )

            hover_card = (
                f"<span style='float:right; padding-left:14px; "
                f"font-size:8px;'>"
                f"[{html.escape(str(row['Type']).upper())}]</span>"
                f"<b>Task:</b> {row['Task']}<br><b>Duration:</b> "
                f"{row['Duration']}<br><b>Target:</b> {row['Target Date']}"
            )
            description = _format_description(row.get("Description", ""))
            if description:
                hover_card += f"<br><br>{description}"

            hover_meta = dict(
                taskId=task_id, groups=connections,
                jira=jira_url, conf=conf_url,
                bg=task_color, fg=text_color
            )

            fig.add_trace(go.Scatter(
                x=[mid_date, mid_date], y=[row["Y"], text_y],
                mode="lines", line=dict(color=task_color, width=1),
                opacity=0.4, showlegend=False, hoverinfo="skip",
                meta=dict(
                    taskId=task_id, baseOpacity=0.4, groups=connections
                )
            ))

            half_height = 0.02
            box_x = [
                row["Start"], row["End"], row["End"], row["Start"],
                row["Start"]
            ]
            box_y = [
                row["Y"] - half_height, row["Y"] - half_height,
                row["Y"] + half_height, row["Y"] + half_height,
                row["Y"] - half_height
            ]

            show_in_legend = False
            if row["Type"] not in added_legends:
                added_legends.add(row["Type"])
                show_in_legend = True

            fig.add_trace(go.Scatter(
                x=box_x, y=box_y, fill="toself", mode="lines",
                fillcolor=task_color, line=dict(color="black", width=1),
                opacity=0.9, name=str(row["Type"]).title(),
                legendgroup=str(row["Type"]), showlegend=show_in_legend,
                text=hover_card, hoverinfo="none",
                meta=dict(hover_meta, baseOpacity=0.9)
            ))

            fig.add_trace(go.Scatter(
                x=[mid_date], y=[text_y],
                mode="markers",
                marker=dict(size=35, color="rgba(0,0,0,0)"),
                showlegend=False,
                legendgroup=str(row["Type"]),
                text=hover_card,
                hoverinfo="none",
                zorder=4,
                meta=dict(hover_meta, baseOpacity=1.0)
            ))

            fig.add_annotation(
                x=mid_date, y=text_y, text=display_text,
                showarrow=False, align="center", font=dict(
                    size=9, color=text_color
                ),
                bordercolor="black", borderwidth=0.5, borderpad=5,
                bgcolor=task_color, opacity=1.0,
                name=f"task-{task_id}"
            )

    if not df_normal.empty:
        render_plotly_section(df_normal, is_above=True)
    if not df_dep.empty:
        render_plotly_section(df_dep, is_above=False)

    fig.update_layout(
        title=dict(
            text=f"<b>{args.title}</b>", x=0.5, y=0.96,
            font=dict(size=18, color="#1a1a1a")
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            type="date", range=[
                df["Start"].min() - timedelta(days=5),
                df["End"].max() + timedelta(days=10)
            ],
            showgrid=False, zeroline=False, showticklabels=False
        ),
        yaxis=dict(
            range=[min_y, max_y], showgrid=False, zeroline=False,
            showticklabels=False, fixedrange=True
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=0.01, xanchor="center", x=0.5,
            bgcolor="#f8f9fa", bordercolor="gray", borderwidth=1
        ),
        margin=dict(t=80, b=60, l=40, r=40),
        height=850
    )

    fig.write_html(
        args.output, include_plotlyjs='cdn',
        post_script=[_HIGHLIGHT_JS, _TODAY_JS, _TOOLTIP_JS]
    )
