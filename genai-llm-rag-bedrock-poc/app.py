import streamlit as st
import os
from cases import code_generation, translation_nlp, extract_text_from_files

streamlit_user = os.environ['USER']
streamlit_pwd = os.environ['PWD']

def authenticate_user(username, password):
    """Function to authenticate user."""
    return username == streamlit_user and password == streamlit_pwd

def login_page():
    """Function to display the login page."""
    #st.image('binbash_logo.png', width=150)
    st.title("Generative AI AWS Conference")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")
    if login_button:
        if authenticate_user(username, password):
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Username or Password is incorrect")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def main_page():
    st.title('Generative AI AWS Conference')
    cases = {
        "Code Generation": code_generation,
        "Translation and NLP": translation_nlp,
        "Extract Text from Files": extract_text_from_files
    }
    option = st.selectbox('Select a Use Case', list(cases.keys()))
    if option:
        cases[option].run()

def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        main_page()

if __name__ == "__main__":
    main()
