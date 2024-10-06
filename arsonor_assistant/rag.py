import json
import os
import time

from openai import OpenAI
from elasticsearch import Elasticsearch


client = OpenAI()

ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elasticsearch:9200")
INDEX_NAME = os.getenv("INDEX_NAME")
es_client = Elasticsearch(ELASTIC_URL)


def elastic_search(query, category=None):
    search_query = {
        "size": 10,
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title", "tags", "chunk_text"],
                        "type": "best_fields"
                    }
                }
            }
        }
    }
    
    if category is not None:
        search_query["query"]["bool"]["filter"] = {
            "term": {
                "category": category
            }
        }

    response = es_client.search(index=INDEX_NAME, body=search_query)
    
    return [hit['_source'] for hit in response['hits']['hits']]


prompt_template = """
You're an audio engineer and sound designer instructor for beginners.
You're particularly specialized in audio home-studio set-up, computer music production and audio post-production in general (editing, mixing and mastering). 
Answer the QUESTION based on the CONTEXT from our arsonor knowledge database (articles).
Use only the facts from the CONTEXT when answering the QUESTION.
Finally, recommend the top 3 Arsonor articles that are the best to read for answering this question.
For each recommended article, include both its title and URL.

QUESTION: {question}

CONTEXT:
{context}
""".strip()

entry_template = """
ARTICLE: {title}
URL: {url}
KEYWORDS: {tags}
CONTENT: {chunk_text}
""".strip()


def build_prompt(query, search_results):
    context = ""

    for doc in search_results:
        context = context + entry_template.format(**doc) + "\n\n"

    prompt = prompt_template.format(question=query, context=context).strip()
    return prompt


def llm(prompt, model="gpt-4o-mini"):
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}]
        )

        answer = response.choices[0].message.content

        tokens = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        end_time = time.time()
        response_time = end_time - start_time

        return answer, tokens, response_time
    except Exception as e:
        print(f"Error in LLM call: {str(e)}")
        return None, None, None


evaluation_prompt_template = """
You are an expert evaluator for a RAG system.
Your task is to analyze the relevance of the generated answer to the given question.
Based on the relevance of the generated answer, you will classify it
as "NON_RELEVANT", "PARTLY_RELEVANT", or "RELEVANT".

Here is the data for evaluation:

Question: {question}
Generated Answer: {answer}

Please analyze the content and context of the generated answer in relation to the question
and provide your evaluation in parsable JSON without using code blocks:

{{
  "Relevance": "NON_RELEVANT" | "PARTLY_RELEVANT" | "RELEVANT",
  "Explanation": "[Provide a brief explanation for your evaluation]"
}}
""".strip()


def evaluate_relevance(question, answer):
    if answer is None:
        return "ERROR", "Failed to generate answer", {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    
    prompt = evaluation_prompt_template.format(question=question, answer=answer)
    evaluation, tokens, _ = llm(prompt, model="gpt-4o-mini")
    
    if evaluation is None:
        return "ERROR", "Failed to evaluate answer", tokens or {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

    try:
        json_eval = json.loads(evaluation)
        return json_eval['Relevance'], json_eval['Explanation'], tokens
    except json.JSONDecodeError:
        try:
            str_eval = evaluation.rstrip('}') + '}'
            json_eval = json.loads(str_eval)
            return json_eval['Relevance'], json_eval['Explanation'], tokens
        except json.JSONDecodeError:
            return "ERROR", "Failed to parse evaluation", tokens



def calculate_openai_cost(model, tokens):
    if tokens is None:
        return 0
    
    openai_cost = 0

    if model == "gpt-4o-mini":
        openai_cost = (
            tokens["prompt_tokens"] * 0.00015 + tokens["completion_tokens"] * 0.0006
        ) / 1000
    else:
        print("Model not recognized. OpenAI cost calculation failed.")

    return openai_cost


def rag(query, category=None, model="gpt-4o-mini"):
    try:
        search_results = elastic_search(query, category)
        prompt = build_prompt(query, search_results)
        answer, tokens, response_time = llm(prompt, model=model)

        if answer is None:
            return {
                "answer": "I apologize, but I encountered an error while processing your question.",
                "response_time": 0,
                "relevance": "ERROR",
                "relevance_explanation": "Failed to generate answer",
                "model_used": model,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "eval_prompt_tokens": 0,
                "eval_completion_tokens": 0,
                "eval_total_tokens": 0,
                "openai_cost": 0,
            }

        relevance, explanation, eval_tokens = evaluate_relevance(query, answer)
        
        openai_cost = calculate_openai_cost(model, tokens)
        eval_cost = calculate_openai_cost(model, eval_tokens)
        total_cost = openai_cost + eval_cost

        return {
            "answer": answer,
            "response_time": response_time,
            "relevance": relevance,
            "relevance_explanation": explanation,
            "model_used": model,
            "prompt_tokens": tokens["prompt_tokens"],
            "completion_tokens": tokens["completion_tokens"],
            "total_tokens": tokens["total_tokens"],
            "eval_prompt_tokens": eval_tokens["prompt_tokens"],
            "eval_completion_tokens": eval_tokens["completion_tokens"],
            "eval_total_tokens": eval_tokens["total_tokens"],
            "openai_cost": total_cost,
        }
    except Exception as e:
        print(f"Error in RAG process: {str(e)}")
        return {
            "answer": "I apologize, but I encountered an error while processing your question.",
            "response_time": 0,
            "relevance": "ERROR",
            "relevance_explanation": f"Error: {str(e)}",
            "model_used": model,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "eval_prompt_tokens": 0,
            "eval_completion_tokens": 0,
            "eval_total_tokens": 0,
            "openai_cost": 0,
        }