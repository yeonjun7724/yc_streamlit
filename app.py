import streamlit as st

st.title("Welcome to My Streamlit App")
st.write("Hello, world!")
name = st.text_input("이름을 입력하세요:")
if name:
    st.success(f"{name}님 반가워요!")