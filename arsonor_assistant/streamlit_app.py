import streamlit as st
import requests
import json

# Set up the Streamlit app
st.title("LLM-RAG System Interface")

# Section 1: Ask a question
st.header("Ask a Question")

question = st.text_input("Enter your question:")

if st.button("Submit Question"):
    if question:
        # Send the question to the Flask API
        response = requests.post("http://app:5000/question", json={"question": question})
        
        if response.status_code == 200:
            result = response.json()
            conversation_id = result.get("conversation_id")
            st.write(f"Question: {result.get('question')}")
            st.write(f"Answer: {result.get('answer')}")
        else:
            st.error("Error in fetching response. Please try again.")
    else:
        st.error("Please enter a question.")

# Section 2: Provide feedback
st.header("Provide Feedback")

conversation_id = st.text_input("Enter the conversation ID for feedback:")
feedback = st.radio("Was the answer helpful?", options=("Yes", "No"))

feedback_value = 1 if feedback == "Yes" else -1

if st.button("Submit Feedback"):
    if conversation_id:
        # Send the feedback to the Flask API
        feedback_response = requests.post(
            "http://app:5000/feedback", 
            json={"conversation_id": conversation_id, "feedback": feedback_value}
        )
        
        if feedback_response.status_code == 200:
            feedback_result = feedback_response.json()
            st.write(feedback_result.get("message"))
        else:
            st.error("Error in submitting feedback. Please check the conversation ID.")
    else:
        st.error("Please enter a conversation ID.")
