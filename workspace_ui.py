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
        [data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {{
            position: relative !important;
        }}
        [data-testid="stMain"] .st-key-{button_key} {{
            position: absolute !important;
            top: 12px !important;
            right: 24px !important;
            z-index: 1000 !important;
            width: auto !important;
        }}
        @media (max-width: 768px) {{
            [data-testid="stMain"] .st-key-{button_key} {{
                top: 8px !important;
                right: 12px !important;
            }}
        }}
        """

    st.markdown(
        f"""
        <style>
        [data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {{
            padding-top: 0 !important;
            margin-top: 0 !important;
        }}
        [data-testid="stMain"] .block-container {{
            padding-top: 0 !important;
            margin-top: 0 !important;
        }}
        [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.st-key-{button_key}) {{
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
        [data-testid="stMain"] .st-key-{button_key} {{
            display: flex !important;
            justify-content: flex-end !important;
            width: 100% !important;
            margin: 0 !important;
        }}
        html body [data-testid="stMain"] .st-key-{button_key} [data-testid="stButton"] > button {{
            width: auto !important;
            min-width: 0 !important;
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
        html body [data-testid="stMain"] .st-key-{button_key} [data-testid="stButton"] > button:hover {{
            background: #fff !important;
            box-shadow: 0 6px 16px rgba(49,99,151,.14) !important;
            transform: translateY(-1px);
        }}
        {pinned_button_styles}
        @media (max-width: 480px) {{
            .workspace-page-brand-copy b {{ font-size: 16px; }}
        }}
        @media (max-width: 768px) {{
            html body [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.st-key-{button_key}) {{
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                align-items: center !important;
                position: relative !important;
                min-height: 40px !important;
                gap: 8px !important;
                margin: 0 0 8px !important;
            }}
            html body [data-testid="stMain"] .st-key-{button_key} [data-testid="stButton"] > button {{
                min-height: 34px !important;
                height: 34px !important;
                padding: 0 14px !important;
                gap: 0 !important;
                text-transform: none !important;
                color: #fff !important;
                background: linear-gradient(105deg, #3478f6, #655eea) !important;
                border: 0 !important;
                border-radius: 999px !important;
                box-shadow: 0 4px 12px rgba(52,120,246,.28) !important;
                -webkit-tap-highlight-color: transparent;
            }}
            html body [data-testid="stMain"] .st-key-{button_key} [data-testid="stButton"] > button:active {{
                transform: scale(.96);
            }}
            html body [data-testid="stMain"] .st-key-{button_key} [data-testid="stButton"] > button p {{
                font-size: 0 !important;
                line-height: 1 !important;
            }}
            html body [data-testid="stMain"] .st-key-{button_key} [data-testid="stButton"] > button p::after {{
                content: "← Back";
                color: #fff !important;
                -webkit-text-fill-color: #fff !important;
                text-transform: none;
                font: 700 12px 'Inter', Arial, sans-serif;
                letter-spacing: .2px;
            }}
            .workspace-page-brand {{ min-height: 36px; gap: 7px; min-width: 0; }}
            .workspace-page-brand-mark {{ flex: 0 0 auto; width: 32px; height: 32px; font-size: 20px; }}
            .workspace-page-brand-copy {{ min-width: 0; }}
            .workspace-page-brand-copy small {{
                font-size: 7px;
                letter-spacing: 1.2px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            html body [data-testid="stMain"] .st-key-{button_key},
            html body [data-testid="stMain"] .st-key-{button_key} [data-testid="stButton"],
            html body [data-testid="stHorizontalBlock"]:has(.st-key-{button_key})
            > [data-testid="stColumn"]:has(.st-key-{button_key}) > [data-testid="stVerticalBlock"] {{
                width: max-content !important;
                min-width: 0 !important;
                flex: 0 0 auto !important;
            }}
            html body [data-testid="stHorizontalBlock"]:has(.st-key-{button_key})
            > [data-testid="stColumn"]:has(.st-key-{button_key}) {{
                position: absolute !important;
                top: 2px !important;
                right: 0 !important;
                z-index: 20 !important;
                display: flex !important;
                flex: 0 0 auto !important;
                width: auto !important;
                min-width: 0 !important;
                max-width: none !important;
                justify-content: flex-end !important;
            }}
            html body [data-testid="stHorizontalBlock"]:has(.st-key-{button_key})
            > [data-testid="stColumn"]:not(:has(.st-key-{button_key})) {{
                flex: 1 1 100% !important;
                width: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                padding-right: 88px !important;
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
