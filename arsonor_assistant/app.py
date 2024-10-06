import streamlit as st
import pandas as pd
import time
import uuid

from rag import rag
from db import save_conversation, save_feedback, get_recent_conversations, get_feedback_stats


def print_log(message):
    print(message, flush=True)


def main():

    # Set up the Streamlit app
    st.set_page_config(page_title="Arsonor Assistant", layout="wide")
    st.title("Arsonor Assistant")

    # Session state initialization
    if 'conversation_id' not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
        print_log(f"New conversation started with ID: {st.session_state.conversation_id}")  
    if 'feedback_given' not in st.session_state:
        st.session_state.feedback_given = False
    if 'count' not in st.session_state:
        st.session_state.count = 0
        print_log("Feedback count initialized to 0")
    if 'response_received' not in st.session_state:
        st.session_state.response_received = False

    # Sidebar for settings
    st.sidebar.header("Settings")

    category_options = {
        "None": None,
        "Post-Production": "LA POST-PROD",
        "Home-Studio": "LE HOME STUDIO",
        "Sound Design": "LE SOUND DESIGN",
    }

    category_display = st.sidebar.selectbox(
        "Select a category (optional):",
        list(category_options.keys()),
    )

    category = category_options[category_display]

    if category:
        print_log(f"User selected category: {category}")
    else:
        print_log("No category selected.")

    # User input form
    with st.form(key='question_form'):
        user_input = st.text_input("Enter your question:")
        submit_button = st.form_submit_button(label='Ask')
    

    if submit_button:
        print_log(f"User asked: '{user_input}'")
        with st.spinner('Processing...'):
            print_log(f"Getting answer from assistant")
            start_time = time.time()
            answer_data = rag(user_input, category=None, model='gpt-4o-mini')
            end_time = time.time()
            print_log(f"Answer received in {end_time - start_time:.2f} seconds")
            
            st.success("Completed!")

            print(answer_data)
            st.write(answer_data['answer'])

            st.session_state.response_received = True
            st.session_state.feedback_given = False
            print_log("Response generated. Feedback is now allowed.")

            try:
                # st.markdown(f"**Answer:** {answer_data['answer']}")

                if 'response_time' in answer_data:
                    st.markdown(f"**Response Time:** {answer_data['response_time']:.2f} seconds")
                if 'relevance' in answer_data:
                    st.markdown(f"**Relevance:** {answer_data['relevance']}")
                if 'model_used' in answer_data:
                    st.markdown(f"**Model Used:** {answer_data['model_used']}")
                if 'total_tokens' in answer_data:
                    st.markdown(f"**Total Tokens:** {answer_data['total_tokens']}")
                if 'openai_cost' in answer_data and answer_data['openai_cost'] > 0:
                    st.markdown(f"**OpenAI Cost:** ${answer_data['openai_cost']:.4f}")
            except KeyError as e:
                st.error(f"Unexpected response format: missing key {str(e)}")
                return

            # Save conversation to database
            print_log("Saving conversation to database")
            category_to_save = category if category is not None else 'Unknown'
            save_conversation(st.session_state.conversation_id, user_input, answer_data, category_to_save)
            print_log("Conversation saved successfully")


    # Feedback buttons section
    st.subheader("Feedback")

    def on_positive_feedback():
        if not st.session_state.feedback_given and st.session_state.response_received:
            st.session_state.count += 1
            st.session_state.feedback_given = True
            print_log(f"Positive feedback received. New count: {st.session_state.count}")
            save_feedback(st.session_state.conversation_id, 1)
            print_log("Positive feedback saved to database")

    def on_negative_feedback():
        if not st.session_state.feedback_given and st.session_state.response_received:
            st.session_state.count -= 1
            st.session_state.feedback_given = True
            print_log(f"Negative feedback received. New count: {st.session_state.count}")
            save_feedback(st.session_state.conversation_id, -1)
            print_log("Negative feedback saved to database")

    col1, col2 = st.columns(2)

    with col1:
        st.button("👍", 
                on_click=on_positive_feedback,
                disabled=not st.session_state.response_received or st.session_state.feedback_given)

    with col2:
        st.button("👎", 
                on_click=on_negative_feedback,
                disabled=not st.session_state.response_received or st.session_state.feedback_given)

    # Display current feedback count in the sidebar
    st.sidebar.markdown(f"**Current Count:** {st.session_state.count}")


    # Display recent conversations
    st.subheader("Recent Conversations")
    relevance_filter = st.selectbox("Filter by relevance:", ["All", "RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT"])
    try:
        recent_conversations = get_recent_conversations(limit=5, relevance=relevance_filter if relevance_filter != "All" else None)
        
        if recent_conversations:
            df_columns = [
                "question", "answer", "category", "model_used", "relevance", 
                "relevance_explanation"
            ]
            
            # Convert the recent conversations into a DataFrame
            df_recent_conversations = pd.DataFrame(recent_conversations)
            
            # Select only the columns we want to display
            df_display = df_recent_conversations[df_columns].copy()
            
            # Display the DataFrame
            st.dataframe(df_display)
        else:
            st.write("No recent conversations to display.")
    except Exception as e:
        st.error(f"Error fetching recent conversations: {str(e)}")

    
    # Display feedback stats
    st.subheader("Feedback Statistics")
    try:
        feedback_stats = get_feedback_stats()
        
        if feedback_stats:
            # Convert feedback stats into a DataFrame
            df_feedback_stats = pd.DataFrame([feedback_stats])
            st.dataframe(df_feedback_stats)
        else:
            st.write("No feedback statistics available.")
    except Exception as e:
        st.error(f"Error fetching feedback statistics: {str(e)}")


    

print_log("Streamlit app loop completed")


if __name__ == "__main__":
    print_log("Arsonor Assistant application started")
    main()
