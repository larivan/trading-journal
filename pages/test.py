import streamlit as st
import pandas as pd

# Initialize session state if not already set
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame({
        "Nom": ["Alice", "Bob", "Charlie"],
        "Âge": [25, 30, 35],
        "Ville": ["Paris", "Londres", "Berlin"]
    })


@st.fragment
def display_dataframe_fragment():
    """
    Fragment to display the current DataFrame.
    """
    st.subheader('Current DataFrame')
    st.dataframe(st.session_state.data)


@st.fragment
def add_row_fragment():
    """
    Fragment to add a new row to the DataFrame.
    """
    st.subheader('Add a Row')
    with st.form(key="add_row_form"):
        name = st.text_input('Name')
        age = st.number_input('Age', min_value=0, max_value=120, step=1)
        city = st.text_input('City')
        submitted = st.form_submit_button("Add")
        if submitted:
            if name and city:
                new_row = {"Nom": name, "Âge": age, "Ville": city}
                st.session_state.data = pd.concat(
                    [st.session_state.data, pd.DataFrame([new_row])], ignore_index=True
                )
                st.success('Row added successfully.')
                st.rerun()
            else:
                st.error('Please fill in all required fields.')


@st.fragment
def edit_row_fragment():
    """
    Fragment to edit an existing row in the DataFrame.
    """
    st.subheader('Edit a Row')
    if not st.session_state.data.empty:
        row_index = st.selectbox(
            'Select a row to edit (by index)',
            st.session_state.data.index
        )
        row_data = st.session_state.data.iloc[row_index]
        with st.form(key='edit_row_form'):
            name = st.text_input('Name', value=row_data['Nom'])
            age = st.number_input('Age', min_value=0,
                                  max_value=120, step=1, value=row_data["Âge"])
            city = st.text_input('City', value=row_data['Ville'])
            submitted = st.form_submit_button('Edit')
            if submitted:
                st.session_state.data.loc[row_index] = [name, age, city]
                st.success(f'Row {row_index} edited successfully.')
                st.rerun()
    else:
        st.warning('No data available for editing.')


@st.fragment
def delete_row_fragment():
    """
    Fragment to delete a row from the DataFrame.
    """
    st.subheader('Delete a Row')
    if not st.session_state.data.empty:
        row_index = st.selectbox(
            "Select a row to delete (by index)",
            st.session_state.data.index
        )
        if st.button('Delete'):
            st.session_state.data = st.session_state.data.drop(
                row_index).reset_index(drop=True)
            st.success(f'Row {row_index} deleted successfully.')
            st.rerun()
    else:
        st.warning('No data available for deletion.')


# Main interface
st.title("Interactive DataFrame Management")

# Call the fragments
display_dataframe_fragment()
add_row_fragment()
edit_row_fragment()
delete_row_fragment()
