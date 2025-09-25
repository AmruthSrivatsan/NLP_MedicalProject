# Lab Report Digitization API

This project exposes a FastAPI service for OCR-driven lab report digitization. You can run it directly on your machine or inside Docker.

## Local Development
1. **Clone the repo**
   ```bash
   git clone https://github.com/your-username/NLP_MedicalProject.git
   cd NLP_MedicalProject
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Start the API**
   ```bash
   python -m uvicorn app:app --reload
   ```
4. Open http://127.0.0.1:8000 in your browser to access the UI served from `static/index.html`.

## Docker Usage
1. **Build the image**
   ```bash
   docker build -t nlp-medical-api .
   ```
2. **Run the container**
   ```bash
   docker run --rm -p 8000:8000 -v $(pwd)/data:/app/data nlp-medical-api
   ```
   Mounting the local `data/` directory keeps uploads and generated outputs between runs.
3. Open http://127.0.0.1:8000 to interact with the application.
