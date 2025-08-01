import streamlit as st
import requests
import base64
from urllib.parse import urlparse

# ----------------------------
# 🔧 Groq model config
# ----------------------------
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"


def query_groq(prompt, groq_api_key):
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a senior developer writing high-quality documentation."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ----------------------------
# 🔧 GitHub functions
# ----------------------------
def get_repo_details(url):
    path = urlparse(url).path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path.split("/")[0], path.split("/")[1]


def fetch_repo_files(owner, repo, token):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(api_url, headers=headers)
    if res.status_code != 200:
        raise Exception(f"❌ Failed to fetch repo contents.\n\n{res.text}")
    return res.json()


def get_file_content(file_url, token):
    headers = {"Authorization": f"token {token}"}
    res = requests.get(file_url, headers=headers)
    return base64.b64decode(res.json()["content"]).decode("utf-8")


def update_readme(owner, repo, token, new_readme, sha=None):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
    headers = {"Authorization": f"token {token}"}
    data = {
        "message": "📝 Auto-updated README using AI (Groq)",
        "content": base64.b64encode(new_readme.encode()).decode("utf-8"),
        "sha": sha
    }
    response = requests.put(api_url, headers=headers, json=data)
    if response.status_code not in [200, 201]:
        raise Exception(f"❌ Failed to update README: {response.text}")


# ----------------------------
# 🚀 Streamlit Interface
# ----------------------------
st.set_page_config(page_title="AI README Generator", page_icon="🤖")
st.title("🤖 Auto-Generate GitHub README (Groq Edition)")
st.write("Upload your GitHub repo URL and generate a README using Llama3 via Groq — no HuggingFace needed.")

github_url = st.text_input("🔗 GitHub Repo URL (public)")
github_token = st.text_input("🔐 GitHub Token", type="password")
groq_token = st.text_input("🚀 Groq API Key", type="password")

if st.button("Generate & Update README"):
    try:
        with st.spinner("🔍 Fetching repo contents..."):
            owner, repo = get_repo_details(github_url)
            contents = fetch_repo_files(owner, repo, github_token)

            all_code = ""
            readme_sha = None
            for file in contents:
                if file["name"].lower() == "readme.md":
                    readme_sha = file["sha"]
                    continue
                if file["type"] == "file" and file["name"].endswith((".py", ".js", ".java", ".md","ipynb")):
                    code = get_file_content(file["url"], github_token)
                    all_code += f"\n\n# {file['name']}\n{code}"

        with st.spinner("🤖 Generating README using Groq LLM..."):
            prompt = f"""
You are a senior developer and technical writer.

Your task is to directly generate a complete **README.md** file in GitHub markdown format — without any introductory statements or explanations.

✍️ The README should include:
1. **Project Title** — A clear and relevant heading.
2. **Problem Statement** — A concise summary of the problem the project solves.
3. **Dependencies and Requirements** — List required libraries, tools, and Python version.
4. **Project Structure** — Brief description of each major file/folder.
5. **How to Run** — Setup instructions in steps.
6. **Ideology and Solution** — Explain how the code works and solves the problem.
7. **Technologies Used** — Tools, libraries, frameworks involved.
8. **Contact** — End with: "For any queries, reach out to konashankar097@gmail.com"

📌 Rules:
- Do **not** start with statements like “Here is your README” or “Below is the file”.
- Start directly with the project title or `# Project Title`.
- Use proper GitHub markdown formatting, bold headings, clean spacing, and bullet points.

Here is the project code you need to analyze:
{all_code}
"""


            new_readme = query_groq(prompt, groq_token)

        with st.spinner("📦 Updating README in GitHub..."):
            update_readme(owner, repo, github_token, new_readme, readme_sha)

        st.success("✅ README successfully generated and pushed to GitHub!")
        st.subheader("📄 New README Preview")
        st.code(new_readme)

    except Exception as e:
        st.error(f"⚠️ {e}")


