import argparse
import os
import sys
from src.data_loader import DataLoader
from src.png_generator import generate_png_timeline
from src.html_generator import generate_html_timeline


def main():
    help_epilog = (
        "DATE FORMAT LAYOUT REQUIREMENT:\n"
        "  Set your regional formatting mode using the '--date-format' / "
        "'-df' parameter:\n"
        "  -df eu  -> European / Indian layout style (DD.MM.YYYY) - "
        "[DEFAULT]\n"
        "  -df us  -> American layout style (MM/DD/YYYY)\n"
        "  -df iso -> Asian / International style (YYYY-MM-DD)\n\n"
        "MULTI-LINK ECOSYSTEM HOOKS (v1.2.2):\n"
        "  Add optional columns named 'Jira Link' and/or 'Confluence Link' "
        "to your file.\n"
        "  Interactive buttons [Jira] and [Conf] will emerge dynamically "
        "inside the HTML callout boxes.\n\n"
        "LINKED TASK GROUPS (HTML only):\n"
        "  Add an optional column named 'Connections' holding a ';' "
        "separated list of keys.\n"
        "  Tasks sharing a key are highlighted together when any one of "
        "them is clicked.\n\n"
        "TASK DESCRIPTIONS (HTML only):\n"
        "  Add an optional column named 'Description' to show extra detail "
        "in the hover tooltip."
    )

    parser = argparse.ArgumentParser(
        description=(
            "Chronos CLI v1.3.0 - Highly optimized timeline generator "
            "supporting PNG and HTML output formats with custom dual "
            "Jira & Confluence links."
        ),
        epilog=help_epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-f", "--file", required=True,
        help="Path or name of the input CSV or Excel data file.",
    )
    parser.add_argument(
        "-t", "--title", required=True,
        help="The main title text displayed at the top of the timeline chart.",
    )
    parser.add_argument(
        "-o", "--output", required=False,
        default="project_timeline_output.png",
        help="Optional: Output file path. Use '.png' extension for image or "
        "'.html' for interactive view. "
        "Defaults to 'project_timeline_output.png'."
    )
    parser.add_argument(
        "-df", "--date-format", required=False, default="eu",
        choices=["us", "eu", "iso"],
        help="Optional: Date format processing mode for international teams.\n"
             "  eu  : Enforce European/Indian format (DD/MM/YYYY) - DEFAULT\n"
             "  us  : Enforce US format (MM/DD/YYYY)\n"
             "  iso : Enforce Asian/Standard format (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    file_str = str(args.file).replace("(", "").replace(")", "")
    file_str = file_str.replace("'", "").replace('"', "").strip()
    if file_str.endswith(","):
        file_str = file_str[:-1].strip()

    title_str = str(args.title).replace("(", "").replace(")", "")
    title_str = title_str.replace("'", "").replace('"', "").strip()
    if title_str.endswith(","):
        title_str = title_str[:-1].strip()

    output_str = str(args.output).replace("(", "").replace(")", "")
    output_str = output_str.replace("'", "").replace('"', "").strip()
    if output_str.endswith(","):
        output_str = output_str[:-1].strip()

    date_mode = str(args.date_format).replace("(", "").replace(")", "")
    date_mode = date_mode.replace("'", "").replace('"', "").strip()
    if date_mode.endswith(","):
        date_mode = date_mode[:-1].strip()

    output_ext = os.path.splitext(output_str)[1].lower()

    if output_ext not in [".png", ".html"]:
        print(
            "Error: Invalid output extension. Only .png/.html are supported."
        )
        sys.exit(1)

    # Invoke DataLoader class to safely handle parsing pipeline routing
    loader = DataLoader(file_str, date_mode=date_mode)
    df = loader.get_clean_data()

    # Re-assign safe binding strings to argument parameters object
    args.file = file_str
    args.title = title_str
    args.output = output_str

    if output_ext == ".png":
        generate_png_timeline(df, loader.unique_types, loader.colors, args)
    elif output_ext == ".html":
        generate_html_timeline(df, loader.colors, args)

    print(
        f"Success! Chronos CLI generated and saved your timeline asset "
        f"as '{output_str}' using format mode '{date_mode}'."
    )


if __name__ == "__main__":
    main()
