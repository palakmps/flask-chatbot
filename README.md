# Flask Chatbot with Document Reading and Q&A
 
This is a Flask-based chatbot application capable of:
 
- Answering FAQs using fuzzy matching
- Handling general questions using a Hugging Face transformer (`deepset/roberta-base-squad2`)
- Showing local time for valid cities
- Converting currencies using a live API
- Reading and extracting content from uploaded PDF or text files
 
## 🚀 Features
 
- NLP-based Q&A using Transformers
- Currency conversion with live exchange rates
- Time zone queries by city
- Document reader (PDF, TXT)
- Web UI with Flask templates
 
## 🐳 Running Locally with Docker
 
```bash
docker build -t chatbot-app .
docker run -p 7860:7860 chatbot-app