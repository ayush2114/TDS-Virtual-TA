# 💡 LLM-Powered TDS Companion

A lightweight, intelligent assistant for exploring and understanding content from the **Tools in Data Science** (TDS) course, powered by LLMs. This project crawls and parses course pages and discussions from IITM's Discourse forums, converts them into semantic Markdown chunks, generates vector embeddings, and allows intelligent querying and interaction.

---

## 🚀 Features

- 🌐 **Web Crawler**: Uses Playwright to extract content from the TDS course site.
- 🧠 **Semantic Chunking**: Splits content into meaningful segments using `semantic-text-splitter`.
- 🖼️ **Image Understanding**: Optionally uses Gemini or OpenAI models to describe attached images.
- 🗂️ **Vector Embedding**: Embeds chunks using Nomic or OpenAI for downstream semantic search.
- 🔍 **Search & Retrieval**: Enables RAG-style interaction for answering course-related questions.
- ⚙️ **Prompt Testing with Promptfoo**: Compatible with prompt-based evaluation using `promptfoo`.
- 🔄 **CI/CD via GitHub Actions**: Auto-syncs with Hugging Face Spaces upon each push.

---

## 📁 Project Structure

├── tds_pages_md/ # Crawled markdown pages from the official TDS course site
├── discourse_md/ # Markdown files generated from forum discussions
├── scripts/ # Scripts to crawl, convert, embed, and serve
├── app.py # Entry point for web-based or CLI interaction
├── course_content.npz # Precomputed embeddings and chunks (optional)
├── metadata.json # Metadata about crawled pages
├── README.md # This file
└── .github/workflows/ # GitHub Actions for syncing to Hugging Face

yaml
Copy
Edit

---

## ⚙️ Setup Instructions

### 🔧 Requirements

- Python 3.9+
- `poetry` or `pip`
- Hugging Face account
- (Optional) OpenAI or Google Gemini API keys

### 🐍 Install dependencies

```bash
pip install -r requirements.txt
Or use poetry install if using poetry.

🌐 Crawl and Process Content
bash
Copy
Edit
python crawl_tds.py                # Crawl course website
python discourse_to_md.py         # Convert Discourse JSON to Markdown
python embed_chunks.py            # Generate and cache embeddings
🧪 Test with Promptfoo
To test your app with shared prompt evaluations:

bash
Copy
Edit
# Start your local server or interface
python app.py

# Then test via hosted promptfoo evaluation:
# Replace with your endpoint and token if needed
Promptfoo is optional, but helps improve prompt reliability and behavior testing.

🔄 Syncing with Hugging Face
This project uses GitHub Actions to automatically deploy to Hugging Face Spaces. On every push to main, the codebase is synced.

🌐 Hosted App
👉 Try it on Hugging Face Spaces

🧠 Models Used
You can configure the backend to use any of the following for embeddings or vision:

[OpenAI (text-embedding-3-small, gpt-4o)]

[Gemini 2.5 (via Google Generative AI API)]

[Nomic Embeddings for cost-effective open-source options]

💬 Example Use Cases
“What is the main idea behind Week 3?”

“Summarize the key discussion in the deployment tools thread.”

“What does this image in the course material describe?”

🙌 Contributing
Contributions are welcome! Feel free to open issues, feature requests, or pull requests.

📜 License
This project is licensed under the MIT License.

✨ Acknowledgements
IITM Online Degree Team

Hugging Face for Spaces

OpenAI / Google for API support

Community TAs for forum discussions