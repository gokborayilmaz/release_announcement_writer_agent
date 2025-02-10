import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from upsonic import Agent, Task, ObjectResponse
from upsonic.client.tools import Search

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the AI agent
announcement_agent = Agent("GitHub Release Announcement Agent", model="azure/gpt-4o", reflection=True)

# Define the Response Format for tasks
class ReleaseDataResponse(ObjectResponse):
    release_title: str
    release_notes: str

class Announcement(ObjectResponse):
    content: str

@app.post("/generate-announcements/")
async def generate_announcements(input_data: dict):
    """Generates platform-specific announcements for a GitHub release."""
    try:
        github_release_url = input_data.get('github_release_url')
        company_url = input_data.get('company_url')
        github_description = input_data.get('github_description')

        if not github_release_url or not company_url or not github_description:
            raise HTTPException(status_code=400, detail="Missing required fields.")

        # Task 1: Fetch release data
        release_task = Task(
            f"Fetch and analyze release data from {github_release_url}.",
            tools=[Search],
            response_format=ReleaseDataResponse
        )
        announcement_agent.do(release_task)
        release_data = release_task.response

        if not release_data:
            raise HTTPException(status_code=500, detail="Failed to fetch release data.")

        # Define announcement tasks
        platforms = {
            "LinkedIn": "Generate a corporate-style announcement based on the release details.",
            "Reddit": "Generate a highly technical announcement based on the release details.",
            "Discord": "Generate a community-friendly announcement based on the release details.",
            "Twitter": "Generate a fun, emoji-rich announcement based on the release details."
        }

        announcements = {}
        for platform, description in platforms.items():
            task = Task(
                description,
                tools=[Search],
                response_format=Announcement,
                context=[release_data]
            )
            announcement_agent.do(task)
            try:
                announcements[platform] = task.response.dict(exclude={"platform"})
            except Exception as e:
                announcements[platform] = {"error": f"Failed to generate announcement for {platform}: {str(e)}"}

        return announcements

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GitHub Release Announcements</title>
        <script src='https://cdn.tailwindcss.com'></script>
    </head>
    <body class="bg-gray-100 flex justify-center items-center h-screen">
        <div class="bg-white p-8 rounded-lg shadow-lg w-[32rem]">
            <h1 class="text-2xl font-bold text-center mb-4">🚀 Generate Platform Announcements</h1>
            <input id="github_release_url" type="text" placeholder="GitHub Release URL" class="w-full p-2 border rounded mb-2">
            <input id="company_url" type="text" placeholder="Company URL" class="w-full p-2 border rounded mb-2">
            <textarea id="product_aim" placeholder="GitHub Description" class="w-full p-2 border rounded mb-2"></textarea>
            <button onclick="generateAnnouncements()" class="bg-blue-500 text-white px-4 py-2 rounded w-full">Generate</button>
            <div id="result" class="mt-4 text-sm text-gray-800 bg-gray-50 p-4 rounded overflow-y-auto h-64"></div>
        </div>
        <script>
            async function generateAnnouncements() {
                const resultDiv = document.getElementById("result");
                resultDiv.innerHTML = "<p class='text-gray-500'>Generating announcements, please wait...</p>";
                const github_release_url = document.getElementById("github_release_url").value;
                const company_url = document.getElementById("company_url").value;
                const github_description = document.getElementById("product_aim").value;

                const response = await fetch(`/generate-announcements/`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ github_release_url, company_url, github_description })
                });
                const data = await response.json();
                document.getElementById("result").innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
