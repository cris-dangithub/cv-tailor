"""reference.json -> the :root block that cv.css consumes.

Derived values (unitless line heights, margins that are differences) are computed here,
not with calc(): calc() cannot divide two lengths into a reliable unitless number.
"""


def css_vars(ref: dict) -> dict:
    p, s, c, r, col, sp = (ref["page"], ref["sizes"], ref["colors"], ref["rules"],
                           ref["columns"], ref["spacing"])
    return {
        "--m-top": f"{p['margin_top']}pt", "--m-right": f"{p['margin_right']}pt",
        "--m-bottom": f"{p['margin_bottom']}pt", "--m-left": f"{p['margin_left']}pt",

        "--s-name": f"{s['name']}pt", "--s-role": f"{s['role']}pt",
        "--s-section": f"{s['section']}pt", "--s-entity": f"{s['entity']}pt",
        "--s-group": f"{s['group']}pt", "--s-position": f"{s['position']}pt",
        "--s-body": f"{s['body']}pt", "--s-meta": f"{s['meta']}pt",
        "--s-factsheet": f"{s['factsheet']}pt", "--s-cert": f"{s['cert_link']}pt",

        "--c-ink": c["ink"], "--c-text": c["text"],
        "--c-link": c["link"], "--c-rule": c["dotted_rule"],

        "--w-section-rule": f"{r['section']['width']}pt",
        "--w-dotted": f"{r['entity']['width']}pt",
        "--dash": f"{r['entity']['dash']}pt",

        "--col-left": f"{col['left']}pt", "--gutter": f"{col['gutter']}pt",
        "--col-right": f"{col['right']}pt",
        "--head-side": f"{col['header_side_pct']}%",
        "--head-center": f"{col['header_center_pct']}%",

        "--gap-name-role": f"{sp['name_to_role'] - s['name']:.2f}pt",
        "--gap-role-header": f"{sp['role_to_header'] - s['role']:.2f}pt",
        "--lh-header": f"{sp['header_leading'] / s['meta']:.3f}",
        "--lh-body": f"{sp['body_line_height']}",
        "--gap-section-above": f"{sp['section_above']}pt",
        "--gap-section-rule": f"{sp['section_to_rule'] - s['section']:.2f}pt",
        "--gap-rule-entry": f"{sp['rule_to_first_entry']}pt",
        "--gap-blocks": f"{sp['between_blocks'] - s['entity']:.2f}pt",
        "--indent": f"{sp['bullet_indent']}pt",
    }
