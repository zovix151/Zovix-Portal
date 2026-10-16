import streamlit as st


def render_workspace_header(
    button_key: str,
    subtitle: str = "AI STUDIO",
    pin_back_button: bool = False,
) -> bool:
    """Render the shared brand and return-to-studio header for workspace pages."""
    pinned_button_styles = ""
    if pin_back_button:
        pinned_button_styles = f"""
        section[data-testid="stMain"] .st-key-{button_key} {{
            position: fixed !important;
            top: 12px !important;
            right: 24px !important;
            z-index: 1000 !important;
            width: auto !important;
        }}
        @media (max-width: 768px) {{
            section[data-testid="stMain"] .st-key-{button_key} {{
                top: 8px !important;
                right: 12px !important;
            }}
        }}
        """

    st.markdown(
        f"""
        <style>
        section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {{
            padding-top: 0 !important;
            margin-top: 0 !important;
        }}
        section[data-testid="stMain"] .block-container {{
            padding-top: 0 !important;
            margin-top: 0 !important;
        }}
        section[data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.st-key-{button_key}) {{
            align-items: center !important;
            margin: 0 0 12px !important;
        }}
        .workspace-page-brand {{
            display: flex;
            align-items: center;
            gap: 9px;
            min-height: 42px;
            color: #163c68;
            font-family: 'Inter', Arial, sans-serif;
        }}
        .workspace-page-brand-mark {{
            display: flex;
            width: 36px;
            height: 36px;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
            background: linear-gradient(135deg, #16c6dc, #6959ed);
            box-shadow: 0 4px 12px rgba(58, 102, 206, .2);
            color: #fff;
            font-size: 24px;
            font-weight: 850;
        }}
        .workspace-page-brand-copy {{
            display: flex;
            flex-direction: column;
            line-height: 1;
            letter-spacing: .5px;
        }}
        .workspace-page-brand-copy b {{ font-size: 18px; font-weight: 850; }}
        .workspace-page-brand-copy small {{
            margin-top: 4px;
            color: #74869a;
            font-size: 8px;
            font-weight: 750;
            letter-spacing: 2px;
        }}
        section[data-testid="stMain"] .st-key-{button_key} {{
            display: flex !important;
            justify-content: flex-end !important;
            width: 100% !important;
            margin: 0 !important;
        }}
        section[data-testid="stMain"] .st-key-{button_key} button {{
            min-height: 38px !important;
            padding: 0 16px !important;
            color: #2875bc !important;
            background: rgba(255,255,255,.94) !important;
            border: 1px solid #dce8f4 !important;
            border-radius: 22px !important;
            box-shadow: 0 2px 8px rgba(49,99,151,.08) !important;
            font: 650 12px 'Inter', Arial, sans-serif !important;
            white-space: nowrap !important;
        }}
        section[data-testid="stMain"] .st-key-{button_key} button:hover {{
            background: #fff !important;
            box-shadow: 0 6px 16px rgba(49,99,151,.14) !important;
            transform: translateY(-1px);
        }}
        {pinned_button_styles}
        @media (max-width: 480px) {{
            .workspace-page-brand-copy b {{ font-size: 16px; }}
            section[data-testid="stMain"] .st-key-{button_key} button {{
                min-height: 36px !important;
                padding: 0 11px !important;
                font-size: 11px !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    brand_column, back_column = st.columns([0.74, 0.26], vertical_alignment="center")
    with brand_column:
        st.markdown(
            f"""
            <div class="workspace-page-brand" aria-label="Zovix {subtitle}">
              <span class="workspace-page-brand-mark">Z</span>
              <span class="workspace-page-brand-copy">
                <b>ZOVIX</b><small>{subtitle}</small>
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with back_column:
        return st.button(
            "← Back to Studio",
            key=button_key,
            type="secondary",
            width="content",
        )
