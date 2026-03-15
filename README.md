 
# CookSafe AI - Stealth Safety Assistant 🛡️🍳

**CookSafe AI** is a dual-purpose web application developed for a **BEST Bucharest Hackathon**. It functions as a friendly cooking assistant while secretly providing a lifeline for users in dangerous domestic situations.

## 🌟 The Core Concept
The application uses a "stealth" interface to protect user privacy. To a casual observer, it appears to be a standard recipe site. However, the backend monitors chat inputs for specific safety-related keywords. When a risk is detected, it activates a **Safety Mode** that provides emergency resources and automated SOS actions.

## 🚀 Technical Features
- **Dual-Mode AI:** Uses **GPT-4o-mini** to switch between a "Chef" persona for recipes and an "AI Risk Assessment" module that rates danger levels from 1 to 10.
- **RAG (Retrieval-Augmented Generation):** Provides verified safety advice and expert protocols sourced from official **NCBI** and **WHO** knowledge bases.
- **Agentic Actions:**
  - **SOS Email/WhatsApp:** Automatically drafts formal reports to the police or SOS messages to family, including the user's GPS coordinates.
  - **Hidden Safety Plans:** Generates a fake "Recipe List" (e.g., Chocolate Cake) that hides a comprehensive 5-step emergency safety plan at the bottom of the file.
  - **Stealth UI:** Includes a "Clean Safety" button to quickly clear sensitive messages from the interface.
- **Geolocation Integration:** Queries a local **SQLite** database to find and sort the nearest verified NGOs, police stations, and legal aid based on real-time distance calculations.

## 🛠️ Tech Stack
- **Backend:** Python, Flask
- **Frontend:** HTML5, CSS3, JavaScript
- **Database:** SQLite
- **AI Integration:** OpenAI API (GPT-4o-mini)

## ⚙️ Setup
1. Clone the repository.
2. Install dependencies: `pip install flask flask-cors openai`
3. Set your environment variable: `export OPENAI_API_KEY='your_key_here'`
4. Run the application: `python app.py`
5. The browser will automatically open to `http://127.0.0.1:5000`.

---
*Note: This project was created for educational purposes during a hackathon to demonstrate how AI can be used for social protection.*
