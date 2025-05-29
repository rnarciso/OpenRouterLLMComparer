# app.py (Final Feedback Test Version)
import streamlit as st
import os

# Attempt to write to a direct file log
python_log_file_path = "/app/python_direct_log.txt"
with open(python_log_file_path, "w") as f:
    f.write("FINAL FEEDBACK TEST: Python script execution started.\n")

print("FINAL FEEDBACK TEST: Python script execution started (via print).")
st.error("FINAL FEEDBACK TEST: Streamlit st.error() message from top of script.")

st.title("Final Feedback Test App")
st.write("This is a final attempt to get execution feedback.")

with open(python_log_file_path, "a") as f:
    f.write("FINAL FEEDBACK TEST: Streamlit UI elements (title, write) processed.\n")

print("FINAL FEEDBACK TEST: Streamlit UI elements processed (via print).")

# A simple function call
def test_func():
    with open(python_log_file_path, "a") as f:
        f.write("FINAL FEEDBACK TEST: In test_func.\n")
    print("FINAL FEEDBACK TEST: In test_func (via print).")
    st.write("Output from test_func.")

test_func()

with open(python_log_file_path, "a") as f:
    f.write("FINAL FEEDBACK TEST: Script execution finished.\n")

print("FINAL FEEDBACK TEST: Script execution finished (via print).")
