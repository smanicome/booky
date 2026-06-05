import base64
from pathlib import Path
import streamlit as st
from PIL import Image

_CSS_PATH  = Path(__file__).parent.parent / "static" / "main.css"
_LOGO_PATH = Path(__file__).parent.parent / "static" / "logo.png"


def get_page_icon() -> Image.Image:
    return Image.open(_LOGO_PATH)


def inject_css() -> None:
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_header() -> None:
    logo_b64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
    st.logo(str(_LOGO_PATH))
    st.markdown(f"""
<div class="site-header">
  <img src="data:image/png;base64,{logo_b64}" class="site-header-img" alt="Booky">
  <div class="site-header-text">
    <span class="site-header-logo">Booky</span>
  </div>
</div>
""", unsafe_allow_html=True)
