import streamlit as st
import os
import hashlib

def check_password():
    """Simple password authentication"""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        app_user = os.getenv("APP_USER")
        app_password = os.getenv("APP_PASSWORD")

        if not app_user or not app_password:
            st.error("⚠️ APP_USER and APP_PASSWORD must be set in environment variables")
            st.session_state["password_correct"] = False
            return

        if (st.session_state["username"] == app_user and
            st.session_state["password"] == app_password):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Check if already authenticated
    if "password_correct" not in st.session_state:
        # First run, show inputs
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("### 🔐 Autenticación")
            st.markdown("---")
            st.text_input("👤 Usuario", key="username", placeholder="Ingrese su usuario")
            st.text_input("🔑 Contraseña", type="password", key="password", placeholder="Ingrese su contraseña")
            st.button("🚀 Ingresar", on_click=password_entered, type="primary", use_container_width=True)
        return False
    
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("### 🔐 Autenticación")
            st.markdown("---")
            st.error("😕 Usuario o contraseña incorrectos")
            st.text_input("👤 Usuario", key="username", placeholder="Ingrese su usuario")
            st.text_input("🔑 Contraseña", type="password", key="password", placeholder="Ingrese su contraseña")
            st.button("🚀 Reintentar", on_click=password_entered, type="primary", use_container_width=True)
        return False
    
    else:
        # Password correct - show logout button in sidebar
        with st.sidebar:
            st.markdown("---")
            if st.button("🚪 Cerrar Sesión", type="secondary", use_container_width=True):
                del st.session_state["password_correct"]
                st.rerun()
        return True
        