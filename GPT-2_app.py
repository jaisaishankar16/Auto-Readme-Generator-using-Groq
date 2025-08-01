import streamlit as st
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
import requests
import base64
from urllib.parse import urlparse

# ----------------------------
# ✅ Load GPT-2 locally
# ----------------------------
@st.cache_resource
def load_gpt2_model():
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    model = AutoModelForCausalLM.from_pretrained("gpt2")
    generator = pipeline("text-generation", model=model, tokenizer=tokenizer)
    return generator

generator = load_gpt2_model()

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
        raise Exception(f"❌ Failed to fetch repo contents. Check if the repo exists and the token has access.\n\n{res.text}")
    return res.json()

def get_file_content(file_url, token):
    headers = {"Authorization": f"token {token}"}
    res = requests.get(file_url, headers=headers)
    return base64.b64decode(res.json()["content"]).decode("utf-8")

def update_readme(owner, repo, token, new_readme, sha=None):
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
    headers = {"Authorization": f"token {token}"}
    data = {
        "message": "📝 Auto-updated README using AI",
        "content": base64.b64encode(new_readme.encode()).decode("utf-8"),
        "sha": sha
    }
    response = requests.put(api_url, headers=headers, json=data)
    if response.status_code not in [200, 201]:
        raise Exception(f"❌ Failed to update README: {response.text}")

# ----------------------------
# 🚀 Streamlit Interface
# ----------------------------
st.title("🤖 Auto-Generate GitHub README using GPT-2 (Open Source)")
st.write("Enter your public GitHub repo link, and get a smart README auto-generated using a local GPT-2 model.")

github_url = st.text_input("🔗 Public GitHub Repo URL (e.g., https://github.com/user/repo)")
github_token = st.text_input("🔐 GitHub Access Token", type="password")

if st.button("🚀 Generate README"):
    try:
        with st.spinner("📂 Fetching repo files..."):
            owner, repo = get_repo_details(github_url)
            contents = fetch_repo_files(owner, repo, github_token)

            all_code = ""
            readme_sha = None
            for file in contents:
                if file["name"].lower() == "readme.md":
                    readme_sha = file["sha"]
                    continue
                if file["type"] == "file" and file["name"].endswith((".py", ".js", ".java", ".md")):
                    code = get_file_content(file["url"], github_token)
                    all_code += f"\n\n# {file['name']}\n{code}"

        with st.spinner("🧠 Generating README using GPT-2..."):
            prompt = f"You are an expert developer. Write a professional README.md file with title, summary, features, how to run, and tech stack based on the following code:\n\n{all_code[:1000]}"
            output = generator(prompt, max_new_tokens=300, do_sample=True, temperature=0.7)
            new_readme = output[0]['generated_text']

        with st.spinner("📤 Updating README in GitHub repo..."):
            update_readme(owner, repo, github_token, new_readme, readme_sha)

        st.success("✅ README generated and updated successfully!")

        st.subheader("📄 New README Content:")
        st.code(new_readme)

    except Exception as e:
        st.error(f"⚠️ {e}")
