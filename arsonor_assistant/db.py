import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from psycopg2.extras import DictCursor
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid

tz = ZoneInfo("Europe/Brussels")

# Create a connection pool
pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=os.getenv("POSTGRES_HOST"),
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)

@contextmanager
def get_db_connection():
    conn = pool.getconn()
    conn.set_client_encoding('UTF8')
    try:
        yield conn
    finally:
        pool.putconn(conn)

def generate_unique_id():
    return str(uuid.uuid4())

def init_db():
    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS feedback")
                cur.execute("DROP TABLE IF EXISTS conversations")

                cur.execute("""
                    CREATE TABLE conversations (
                        id TEXT PRIMARY KEY,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        category TEXT NOT NULL,
                        model_used TEXT NOT NULL,
                        response_time FLOAT NOT NULL,
                        relevance TEXT NOT NULL,
                        relevance_explanation TEXT NOT NULL,
                        prompt_tokens INTEGER NOT NULL,
                        completion_tokens INTEGER NOT NULL,
                        total_tokens INTEGER NOT NULL,
                        eval_prompt_tokens INTEGER NOT NULL,
                        eval_completion_tokens INTEGER NOT NULL,
                        eval_total_tokens INTEGER NOT NULL,
                        openai_cost FLOAT NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE feedback (
                        id SERIAL PRIMARY KEY,
                        conversation_id TEXT REFERENCES conversations(id),
                        feedback INTEGER NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                    )
                """)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error initializing database: {e}")
            conn.rollback()
            return False

def save_conversation(conversation_id, question, answer_data, category, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(tz)

    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversations 
                    (id, question, answer, category, model_used, response_time, relevance, 
                    relevance_explanation, prompt_tokens, completion_tokens, total_tokens, 
                    eval_prompt_tokens, eval_completion_tokens, eval_total_tokens, openai_cost, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        conversation_id,
                        question,
                        answer_data["answer"],
                        category,
                        answer_data["model_used"],
                        answer_data["response_time"],
                        answer_data["relevance"],
                        answer_data["relevance_explanation"],
                        answer_data["prompt_tokens"],
                        answer_data["completion_tokens"],
                        answer_data["total_tokens"],
                        answer_data["eval_prompt_tokens"],
                        answer_data["eval_completion_tokens"],
                        answer_data["eval_total_tokens"],
                        answer_data["openai_cost"],
                        timestamp
                    ),
                )
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            print(f"Duplicate ID {conversation_id} detected. Generating a new ID.")
            new_id = generate_unique_id()
            save_conversation(new_id, question, answer_data, category, timestamp)

def save_feedback(conversation_id, feedback, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(tz)

    with get_db_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO feedback (conversation_id, feedback, timestamp) VALUES (%s, %s, %s)",
                    (conversation_id, feedback, timestamp),
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error saving feedback: {e}")

def get_recent_conversations(limit=5, relevance=None):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            query = """
                SELECT c.*, f.feedback
                FROM conversations c
                LEFT JOIN feedback f ON c.id = f.conversation_id
            """
            if relevance:
                query += " WHERE c.relevance = %s"
                params = (relevance, limit)
            else:
                params = (limit,)
            
            query += " ORDER BY c.timestamp DESC LIMIT %s"
            
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

def get_feedback_stats():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT 
                    SUM(CASE WHEN feedback > 0 THEN 1 ELSE 0 END) as thumbs_up,
                    SUM(CASE WHEN feedback < 0 THEN 1 ELSE 0 END) as thumbs_down
                FROM feedback
            """)
            result = cur.fetchone()
            if result:
                return dict(result)
            return {"thumbs_up": 0, "thumbs_down": 0}