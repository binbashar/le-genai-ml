import streamlit as st
import os
import hashlib

def check_password():
    """Simple password authentication"""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (st.session_state["username"] == os.getenv("APP_USER") and
            st.session_state["password"] == os.getenv("APP_PASSWORD")):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs
        st.markdown("### 🔐 Autenticación")
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password")
        st.button("Ingresar", on_click=password_entered)
        return False
    
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        st.markdown("### 🔐 Autenticación")
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password")
        st.button("Ingresar", on_click=password_entered)
        st.error("😕 Usuario o contraseña incorrectos")
        return False
    
    else:
        # Password correct
        return True