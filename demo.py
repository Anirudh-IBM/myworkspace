from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.requests import Request
import os
import psycopg2
from psycopg2 import Error
from github import Github
import ollama
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
OLLAMA_MODEL_NAME = os.getenv('OLLAMA_MODEL_NAME')

#connect database
def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        return conn
    except Error as e:
        print(e)
        return None

def fetch_pr_data(pr_number):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
    pr = repo.get_pull(pr_number)
    return pr

def run_inference(model, pr_data):
    input_text = pr_data.title + "\n" + pr_data.body
    output = model(input_text)
    return output

def store_result(pr_number, summary):
    conn = connect_to_db()
    if conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO model_responses (pr_number, summary) VALUES (%s, %s)", (pr_number, summary))
        conn.commit()
        cur.close()
        conn.close()
        return True
    return False

@app.get("/docs")
async def get_summary(pr_number: int, store_in_db: bool):
    pr_data = fetch_pr_data(pr_number)
    if pr_data:
        model = ollama.load_model(OLLAMA_MODEL_NAME)
        summary = run_inference(model, pr_data)
        if store_in_db:
            store_result(pr_number, summary)
        return JSONResponse(content={"summary": summary}, media_type="application/json")
    else:
        raise HTTPException(status_code=404, detail="Pull request not found")