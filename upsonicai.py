from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from upsonic import UpsonicClient, Task, AgentConfiguration, ObjectResponse
from upsonic.client.tools import Search
import os

# Initialize the Upsonic client
client = UpsonicClient("localserver")
client.set_config("AZURE_OPENAI_ENDPOINT", os.getenv("AZURE_OPENAI_ENDPOINT"))
client.set_config("AZURE_OPENAI_API_VERSION", os.getenv("AZURE_OPENAI_API_VERSION"))
client.set_config("AZURE_OPENAI_API_KEY", os.getenv("AZURE_OPENAI_API_KEY"))

client.default_llm_model = "azure/gpt-4o"

# Define the FastAPI app
app = FastAPI()

# Add CORS middleware to allow frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the Response Format for tasks
class ReleaseDataResponse(ObjectResponse):
    release_title: str
    release_notes: str

class Announcement(ObjectResponse):
    platform: str
    content: str

# Input model for API
class ReleaseInput(BaseModel):
    github_release_url: str
    company_url: str
    product_aim: str

@app.post("/generate-announcements/")
async def generate_announcements(input_data: ReleaseInput):

    upsonic_agent = AgentConfiguration(
        job_title="Developer Relationship Manager",
        company_url=input_data.company_url,
        company_objective=input_data.product_aim
    )

    # Task 1: Fetch release data
    release_task = Task(
        description="Fetch and analyze release data from the provided GitHub release page.",
        tools=[Search],
        response_format=ReleaseDataResponse,
        context=[input_data.github_release_url]
    )

    client.call(
        release_task
    )

    release_data = release_task.response
    if not release_data:
        raise HTTPException(status_code=500, detail="Failed to fetch release data.")

    # Task 2: Generate LinkedIn announcement
    linkedin_task = Task(
        description="Generate a corporate-style announcement based on the release details.",
        tools=[Search],
        response_format=Announcement,
        context=release_data
    )

    # Task 3: Generate Reddit announcement
    reddit_task = Task(
        description="Generate a highly technical announcement based on the release details.",
        tools=[Search],
        response_format=Announcement,
        context=release_data
    )

    # Task 4: Generate Discord announcement
    discord_task = Task(
        description="Generate a community-friendly announcement based on the release details.",
        tools=[Search],
        response_format=Announcement,
        context=release_data
    )

    # Task 5: Generate Twitter announcement
    twitter_task = Task(
        description="Generate a fun, emoji-rich announcement based on the release details.",
        tools=[Search],
        response_format=Announcement,
        context=release_data
    )

    client.agent(upsonic_agent, linkedin_task)
    client.agent(upsonic_agent, reddit_task)
    client.agent(upsonic_agent, discord_task)
    client.agent(upsonic_agent, twitter_task)

    return {
        "linkedin": linkedin_task.response,
        "reddit": reddit_task.response,
        "discord": discord_task.response,
        "twitter": twitter_task.response
    }

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GitHub Release Announcements</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                line-height: 1.6;
            }
            h1 {
                text-align: center;
            }
            form {
                margin-bottom: 20px;
            }
            pre {
                white-space: pre-wrap;
                word-wrap: break-word;
                background: #f4f4f4;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
            }
            footer {
                text-align: center;
                margin-top: 20px;
                font-size: 0.9em;
                color: #555;
            }
        </style>
    </head>
    <body>
        <h1>Generate Platform Announcements</h1>
        <form id="announcement-form">
            <label for="github_release_url">GitHub Release URL:</label><br>
            <input type="text" id="github_release_url" name="github_release_url" required><br><br>

            <label for="company_url">Company URL:</label><br>
            <input type="text" id="company_url" name="company_url" required><br><br>

            <label for="product_aim">Product Aim:</label><br>
            <textarea id="product_aim" name="product_aim" rows="4" required></textarea><br><br>

            <button type="button" onclick="submitForm()">Generate</button>
        </form>

        <h2>Results</h2>
        <pre id="results"></pre>

        <footer>Powered by UpsonicAI</footer>

        <script>
            async function submitForm() {
                const github_release_url = document.getElementById('github_release_url').value;
                const company_url = document.getElementById('company_url').value;
                const product_aim = document.getElementById('product_aim').value;

                const response = await fetch('/generate-announcements/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ github_release_url, company_url, product_aim })
                });

                const data = await response.json();
                document.getElementById('results').textContent = JSON.stringify(data, null, 2);
            }
        </script>
    </body>
    </html>
    """
