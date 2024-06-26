# app.py
import streamlit as st
import pandas as pd
from typing import List, Dict
from io import BytesIO
import re
import logging

# Root 
logger_name = "app"
logger = logging.getLogger(logger_name)
if not logger.hasHandlers():
    logger.setLevel(logging.DEBUG)
    # File Handler
    file_handler = logging.FileHandler(f'logs/{logger_name}.log', encoding='utf-8-sig')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(r'%(asctime)s [%(name)s, line %(lineno)d] %(levelname)s: %(message)s'))
    logger.addHandler(file_handler)
    # Stream Handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(r'%(message)s'))
    logger.addHandler(stream_handler)

# Define the session state variables if they do not exist
if 'index' not in st.session_state:
    st.session_state.index: int = 0
if 'choices' not in st.session_state:
    st.session_state.choices: List[Dict[str, str]] = []

class MyDataFrame(pd.DataFrame):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        
    def get_label(self, choice: str) -> Dict[str, str] | None:
        pattern = r"\*\*\[(.*?)\]\*\* (.*)"
        match = re.match(pattern, choice)
        if match:
            작업_공사_종류 = match.group(1)
            작업 = match.group(2)
            return {"작업 공사 종류": 작업_공사_종류, "작업": 작업}
        else:
            return None

def convert_df_to_excel(df: pd.DataFrame, new_df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.concat([df, new_df], axis=1).to_excel(writer, index=False)
    processed_data = output.getvalue()
    return processed_data

def selected_columns_page(df_cases, df_classification):
    selected_abbreviation = st.sidebar.radio('약칭을 선택하세요:', df_classification['약칭'].unique())
    with st.sidebar.expander(label='표시할 사고 사례 데이터 열 선택'):
        columns_selected = [column for column in df_cases.columns.tolist() if st.checkbox(column, value=True)]
    display_cases(df_cases, df_classification, columns_selected, selected_abbreviation)

def navigress(total_cases: int) -> None:
    pre, page, nex = st.columns([1, 8, 1])
    with pre:
        if st.session_state.index > 0:
            if st.button('이전', key='prev'):
                st.session_state.index -= 1
                st.experimental_rerun()
    with page:
        st.markdown(f"<p style='font-size:21px; text-align:center;'>{st.session_state.index + 1} / {total_cases}</p>", unsafe_allow_html=True)
    with nex:
        if st.session_state.index + 1 < total_cases:
            if st.button('다음', key='next'):
                st.session_state.index += 1
                st.experimental_rerun()

def display_cases(df_cases, df_classification, columns_selected, selected_abbreviation):
    container = st.container()
    total_cases = len(df_cases)
    container.title('사고 사례 분류기')
    with st.expander("분류 기준 데이터 미리보기"):
        st.write(df_classification[df_classification['약칭'] == selected_abbreviation])
    with st.expander("사고 사례 데이터 미리보기"):
        st.write(df_cases[columns_selected])
    
    if st.session_state.index < total_cases:
        row = df_cases.iloc[st.session_state.index]
        st.markdown(f"<div style='border: 1px solid #e1e1e1; padding: 10px; border-radius: 5px;'><h3>사고 사례 {st.session_state.index + 1}:</h3><ul><li>" + '<li>'.join(f"<b>{col}:</b> {row[col]}" for col in columns_selected) + "</ul></div><br/>", unsafe_allow_html=True)
        selected_row = df_classification[df_classification['약칭'] == selected_abbreviation]
        options: List[str] = [f"**[{row['작업 공사 종류']}]** {row['작업']}" for _, row in selected_row.iterrows()]
        choice = MyDataFrame(df_cases).get_label(st.radio('작업 공사 종류와 작업을 선택하세요:', options=options))
        
        if st.session_state.index >= len(st.session_state.choices):
            st.session_state.choices.append(choice)
        else:
            st.session_state.choices[st.session_state.index] = choice

        navigress(total_cases=total_cases)

    if st.session_state.index + 1 >= total_cases:
        st.success('분류 작업이 완료되었습니다.')
        df_xlsx = convert_df_to_excel(df_cases, pd.DataFrame(st.session_state.choices))
        if st.download_button(
            label="완료된 엑셀 파일 다운로드",
            data=df_xlsx,
            file_name=f'{filename}_분류된_사고_사례.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ):
            st.session_state.index = 0
            st.session_state.choices = []
    else:
        df_xlsx = convert_df_to_excel(df_cases, pd.DataFrame(st.session_state.choices))
        st.download_button(
            label="지금까지 작업한 엑셀 파일 다운로드",
            data=df_xlsx,
            file_name=f'{filename}_분류된_사고_사례(in progress).xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    logger.info(f"{st.session_state.choices = }")

def main():
    st.sidebar.title('파일 업로드')
    uploaded_file1 = st.sidebar.file_uploader("분류 기준 데이터 파일 업로드", type=["xls", "xlsx"])
    uploaded_file2 = st.sidebar.file_uploader("사고 사례 데이터 파일 업로드", type=["xls", "xlsx"])
    global filename
    filename = uploaded_file2.name if uploaded_file2 else '[unknown]'

    if uploaded_file1 and uploaded_file2:
        df_classification = pd.read_excel(uploaded_file1)
        df_classification.ffill(inplace=True)
        df_cases = pd.read_excel(uploaded_file2)
        selected_columns_page(df_cases, df_classification)

if __name__ == '__main__':
    main()
