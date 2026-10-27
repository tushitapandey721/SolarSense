# ☀️ SolarSense AI

**SolarSense AI** is an intelligent, conversational rooftop solar recommendation and assessment platform designed to help homeowners and businesses evaluate their solar potential, estimate system size and savings, upload electricity bills for AI-driven OCR extraction, and seamlessly connect with solar installers.

---

## 🚀 Key Features

- **🤖 Conversational Solar Advisor**: AI-guided assessment state machine that gathers user requirements (monthly bill, rooftop area, roof type, battery preference, location) in an intuitive dialogue.
- **📄 AI Electricity Bill OCR**: Upload electricity bills (PDF, JPEG, PNG, WebP) and automatically extract monthly consumption, sanctioned load, and bill amounts using NVIDIA NIM Vision models.
- **⚡ Smart Solar Calculator**: Instant estimation of recommended system capacity (kW), required roof area (sq. ft), estimated annual generation, system cost, government subsidies, and payback period.
- **📱 Instant WhatsApp Lead Alerts**: Automated real-time notifications to installers/admins via WhatsApp integration when a new lead is registered.
- **📊 Admin Dashboard**: Dedicated portal (`/admin`) to view, manage, and update the status of captured customer inquiries and solar proposals.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask, Flask-CORS
- **AI / LLM**: NVIDIA NIM APIs (`meta/llama-3.1-8b-instruct`, `meta/llama-3.2-11b-vision-instruct`)
- **Document Processing**: `pdf2image`, `Pillow`
- **Frontend**: Responsive HTML5, Vanilla CSS, Vanilla JavaScript
- **Notification**: CallMeBot WhatsApp API
- **Persistence**: Local JSON storage (`data/leads.json`)

---

## 📁 Project Structure

```
solar-sense/
├── app.py                  # Application entry point & Flask initialization
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Ignored files (secrets, venv, data)
├── data/
│   ├── .gitkeep
│   └── leads.json          # Persistent storage for submitted leads
├── models/
│   └── lead.py             # Lead data model definition
├── routes/
│   ├── main.py             # Landing page & assessment page routes
│   ├── chat.py             # Conversational API & bill OCR routes
│   └── admin.py            # Admin lead management routes
├── services/
│   ├── chatbot.py          # Chatbot logic & state machine
│   ├── bill_ocr.py         # Bill document processing & vision extraction
│   ├── nvidia_ai.py        # NVIDIA NIM API integration
│   ├── solar_calc.py       # Solar sizing, subsidy, and cost calculations
│   ├── lead_store.py       # Lead storage & retrieval operations
│   └── whatsapp_notify.py  # WhatsApp notification service
├── static/
│   ├── css/                # Stylesheets
│   ├── js/                 # Client-side scripts
│   └── images/             # Static assets & illustrations
└── templates/
    ├── base.html           # Base layout template
    ├── index.html          # Landing page
    ├── assessment.html     # Interactive assessment flow
    └── admin/              # Admin dashboard templates
```

---

## ⚙️ Getting Started

### 1. Prerequisites
- Python 3.9+ installed on your system
- (Optional) NVIDIA NIM API key for LLM and OCR capabilities

### 2. Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tushitapandey721/SolarSense.git
   cd SolarSense
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\activate

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### 3. Configuration

Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```

Edit `.env` to supply:
- `NVIDIA_API_KEY`: Your NVIDIA NIM key (from [build.nvidia.com](https://build.nvidia.com))
- `SECRET_KEY`: Flask session secret key
- `CALLMEBOT_PHONE` & `CALLMEBOT_API_KEY`: (Optional) For WhatsApp notifications
- `PORT`: Server port (default: `8000`)

### 4. Running the Application

```bash
python app.py
```

Open your browser and navigate to:
- **Home**: `http://localhost:8000`
- **Assessment**: `http://localhost:8000/assessment`
- **Admin**: `http://localhost:8000/admin`

---

## 📄 License

This project is licensed under the MIT License.
