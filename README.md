# AI-Enhanced Reimbursements Management System

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-green.svg)](https://palletsprojects.com/p/flask/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20%7C%20PyMongo-green.svg)](https://www.mongodb.com/)
[![scikit--learn](https://img.shields.io/badge/scikit--learn-1.8.0-red.svg)](https://scikit-learn.org/)
[![Tests](https://img.shields.io/badge/Pytest-30%2F30%20Passed-brightgreen.svg)](https://docs.pytest.org/)

An enterprise-grade, full-stack expense reimbursement platform developed for college project evaluation. The system empowers employees to submit claims and upload supporting bills, while enabling finance administrators to review, approve, or reject requests.

The application is augmented with:
1. **Machine Learning (Random Forest Classifier):** Predicts reimbursement approval risk category (`LIKELY_APPROVED`, `REQUIRES_REVIEW`, `HIGH_REJECTION_RISK`) with statistical confidence scores based strictly on submission-time metadata (zero data leakage).
2. **Generative AI Copilot (Configurable LLM API):** Generates structured reimbursement summaries, policy observations, missing documentation checklists, and review recommendations.
3. **Human-in-the-Loop Governance:** The ML and AI modules provide advisory decision support; final approval and rejection authority remains exclusively with authorized finance personnel.

---

## Table of Contents

- [1. System Architecture](#1-system-architecture)
- [2. Technology Stack](#2-technology-stack)
- [3. Key Features](#3-key-features)
- [4. Database Design & Schema](#4-database-design--schema)
- [5. Machine Learning Methodology](#5-machine-learning-methodology)
- [6. Generative AI Module](#6-generative-ai-module)
- [7. Project Folder Structure](#7-project-folder-structure)
- [8. REST API Reference](#8-rest-api-reference)
- [9. Setup and Local Installation](#9-setup-and-local-installation)
- [10. Running the Application](#10-running-the-application)
- [11. Pre-Seeded Demo Accounts](#11-pre-seeded-demo-accounts)
- [12. Running Automated Tests](#12-running-automated-tests)
- [13. Deliverables & Documentation](#13-deliverables--documentation)
- [14. Known Limitations](#14-known-limitations)

---

## 1. System Architecture

```
+-------------------------------------------------------------------------+
|                        Frontend Presentation Tier                       |
|           HTML5 - CSS3 (Orange Accent) - Vanilla JS - Chart.js          |
+-------------------------------------------------------------------------+
                                    |
                           RESTful JSON (JWT Auth)
                                    |
+-------------------------------------------------------------------------+
|                         Flask Application Tier                          |
|         Blueprints: Auth - Reimbursements - Admin - Analytics           |
+-------------------------------------------------------------------------+
         |                                 |                       |
         v                                 v                       v
+------------------+             +-------------------+    +----------------+
|  MongoDB Atlas   |             |   Random Forest   |    | Generative AI  |
|   (PyMongo DB)   |             |     Pipeline      |    |  LLM Copilot   |
| (Connection Pool)|             |  (scikit-learn)   |    | (Gemini/OpenAI)|
+------------------+             +-------------------+    +----------------+
```

### End-to-End Workflow

1. **Employee Submission:** Employee authenticates, fills in claim details (amount, category, date, description), and attaches a bill (PDF/PNG/JPG).
2. **Backend Validation:** Validates payload, verifies file MIME header magic bytes, saves file with UUID, and creates database record.
3. **ML Risk Inference:** Preprocessing pipeline encodes features, scales numbers, and invokes `RandomForestClassifier.predict_proba()` to compute risk class and confidence.
4. **GenAI Audit Synthesis:** Assembles prompt with claim attributes + ML prediction and queries LLM API (with fallback heuristic engine).
5. **Finance Review:** Authorized finance officers inspect claims, filter by employee/risk/date, view receipts, and make final decisions (with mandatory rejection reasons).
6. **Immutable Audit Trail:** All state transitions and actions are logged to `reimbursement_audit_logs`.

---

## 2. Technology Stack

| Layer | Technologies Used | Description |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript, Chart.js | Professional light theme with orange accent (`#ea580c`), responsive layouts, interactive donut/bar/line charts. |
| **Backend** | Python 3.13, Flask 3.1, Flask-CORS | Modular Blueprint architecture, connection pooling, and RESTful APIs. |
| **Database** | MongoDB Atlas, `pymongo>=4.6.0`, `dnspython>=2.5.0` | Cloud document database with connection pooling, index optimization, and native aggregation pipelines. |
| **Machine Learning** | scikit-learn 1.8, pandas, NumPy, joblib | Preprocessing pipeline (`OneHotEncoder`, `StandardScaler`) with balanced `RandomForestClassifier`. |
| **Generative AI** | Google Gemini API / OpenAI API / Heuristic Engine | Synthesizes structured audit summaries, policy observations, and review actions. |
| **Security** | Werkzeug (`scrypt`), PyJWT | Password hashing, stateless JWT authorization, MIME-type inspection, path traversal protection. |
| **Testing** | pytest | 30 comprehensive automated tests covering all modules with mocked external services. |

---

## 3. Key Features

### For Employees
- Secure registration and login.
- Personal dashboard with spending metrics and historical claim counts.
- Interactive Chart.js visualizations for category breakdown and monthly spending trends.
- Quick submission form with drag-and-drop bill uploads.
- Real-time advisory ML risk prediction meter.
- Generative AI itemized summary and documentation checklist.
- Search and filter personal claims by status or category.

### For Finance & Administrators
- Role-based admin portal with company-wide analytics.
- Real-time high-risk claim alerts surfaced automatically by the ML model.
- Filter claims by employee, status, category, date range, amount range, and ML risk level.
- Secure bill viewer/streamer preventing unauthorized access.
- One-click approval and rejection workflow (mandatory rejection reason for compliance).
- Category management: add new categories and toggle active/inactive status.
- Immutable audit timeline tracking actors, timestamps, and comments for every claim.

---

## 4. Database Design & Schema (MongoDB Atlas)

Database Name: `reimbursement_db`

### Collections

1. **`users`**:
   - `_id` (ObjectId PK), `name` (String), `email` (String, Unique Index), `password_hash` (String, scrypt), `role` (String: `EMPLOYEE`, `ADMIN`), `department` (String), `created_at` (Datetime UTC).
2. **`expense_categories`**:
   - `_id` (ObjectId PK), `name` (String, Unique Index), `description` (String), `is_active` (Boolean), `created_at` (Datetime UTC).
3. **`reimbursement_requests`**:
   - `_id` (ObjectId PK), `employee_id` (ObjectId, Index), `employee_name` (String), `employee_email` (String), `employee_department` (String), `category_id` (ObjectId), `category_name` (String), `amount` (Double), `expense_date` (String YYYY-MM-DD), `description` (String), `receipt_filename` (String), `receipt_path` (String), `status` (String: `PENDING`, `APPROVED`, `REJECTED`, Index), `ml_prediction` (String), `ml_confidence` (Double), `ml_probabilities` (Object), `genai_observations` (String), `missing_documents` (String), `suggested_actions` (String), `rejection_reason` (String), `reviewer_id` (ObjectId), `reviewer_name` (String), `reviewer_comments` (String), `created_at` (Datetime UTC, Index), `updated_at` (Datetime UTC).
4. **`reimbursement_audit_logs`**:
   - `_id` (ObjectId PK), `reimbursement_id` (ObjectId, Index), `actor_id` (ObjectId), `actor_name` (String), `action` (String: `CREATED`, `BILL_UPLOADED`, `APPROVED`, `REJECTED`), `old_status` (String), `new_status` (String), `comments` (String), `created_at` (Datetime UTC).

### Indexes
- **`users`**: Unique index on `email`.
- **`expense_categories`**: Unique index on `name`.
- **`reimbursement_requests`**: Indexes on `employee_id`, `status`, and `created_at`.
- **`reimbursement_audit_logs`**: Index on `reimbursement_id`.

---

## 5. Machine Learning Methodology

- **Algorithm:** Random Forest Classifier (`scikit-learn`).
- **Target Classes:** `LIKELY_APPROVED`, `REQUIRES_REVIEW`, `HIGH_REJECTION_RISK`.
- **Zero-Leakage Feature Set:**
  1. `amount`: numerical expense value in USD.
  2. `category_name`: one-hot encoded categorical variable.
  3. `day_of_week`: submission day (0 = Monday, 6 = Sunday).
  4. `bill_available`: binary receipt indicator (1 = receipt attached, 0 = missing).
  5. `employee_total_past_claims`: count of finalized past claims by this employee.
  6. `employee_past_approval_rate`: historical approval percentage.
  7. `employee_past_rejection_count`: historical rejection count.
  8. `amount_to_category_median_ratio`: normalized ratio against typical category benchmarks.
- **Handling Class Imbalance:** Employs `class_weight='balanced'` inside `RandomForestClassifier`.
- **Performance on Stratified Test Set (20% split):**
  - **Accuracy:** `95.20%`
  - `LIKELY_APPROVED`: Precision 0.99, Recall 0.97, F1 0.98
  - `REQUIRES_REVIEW`: Precision 0.78, Recall 0.89, F1 0.83
  - `HIGH_REJECTION_RISK`: Precision 0.95, Recall 0.82, F1 0.88

---

## 6. Generative AI Module

The Generative AI service coordinates with LLM APIs (Google Gemini or OpenAI compatible endpoints) using environment variables.

### Key Capabilities
- **Concise Summarization:** Condenses business context and attendee details.
- **Expense Pattern Observations:** Flags expenditures exceeding median limits or off-schedule submissions.
- **Missing Information Checklist:** Identifies missing tax invoices, attendee lists, or manager authorizations.
- **Suggested Review Actions:** Proposes clear review steps for the finance team.
- **Security & Reliability:**
  - Prompt injection hardening treats user text as unverified input strings.
  - JSON schema validation verifies output structure.
  - Built-in **Heuristic Audit Engine** takes over gracefully if the external LLM API key is missing or quota is exhausted, ensuring the application remains 100% operational offline.

---

## 7. Project Folder Structure

```
AI-Enhanced Reimbursements Management System/
│
├── app/                                 # Flask Application Package
│   ├── __init__.py                      # Application Factory & Blueprint Registration
│   ├── config.py                        # Centralized Environment Configuration
│   ├── db.py                            # MongoDB Connection Management & Serialization
│   ├── models/                          # Database Data Access Models
│   │   ├── user.py                      # User Authentication & Queries (MongoDB)
│   │   ├── category.py                  # Expense Categories Model (MongoDB)
│   │   └── reimbursement.py             # Claims CRUD, Filtering & Audit Logs (MongoDB)
│   ├── routes/                          # REST API Blueprints
│   │   ├── auth.py                      # /api/auth (Login, Register, Me)
│   │   ├── categories.py                # /api/categories & /api/admin/categories
│   │   ├── reimbursements.py            # /api/reimbursements (Claims, Uploads, ML, AI)
│   │   ├── admin.py                     # /api/admin/reimbursements (Review, Approve, Reject)
│   │   └── analytics.py                 # /api/admin/analytics & /api/employee/analytics
│   ├── services/                        # Business Logic Services
│   │   ├── prediction_service.py        # ML Random Forest Inference Service
│   │   └── genai_service.py             # LLM API & Heuristic Audit Engine
│   └── utils/                           # Helper Utilities
│       ├── auth_utils.py                # scrypt Hashing, JWT Decorators, RBAC Guards
│       ├── file_utils.py                # MIME-Sniffing, UUID Naming, Secure Serving
│       └── validators.py                # Payload & Date Validation Rules
│
├── frontend/                            # Static Single/Multi-Page Web UI
│   ├── index.html                       # Landing Page & Architecture Showcase
│   ├── login.html                       # Sign In Page with Reviewer Quick-Logins
│   ├── register.html                    # Employee Registration Page
│   ├── employee-dashboard.html          # Employee Dashboard & Claim Submission Modal
│   ├── finance-dashboard.html           # Finance Admin Portal & Audit Management
│   ├── submit-reimbursement.html        # Dedicated Reimbursement Submission Form
│   ├── reimbursement-details.html       # Standalone Claim Dossier & AI Panel
│   ├── css/
│   │   └── styles.css                   # Enterprise Orange Accent Theme & Responsive CSS
│   └── js/
│       ├── api.js                       # Centralized API Fetch Wrapper with JWT Header
│       ├── auth.js                      # Session & Route Protection Guards
│       ├── reimbursements.js            # Formatters, Status Badges & Timeline UI
│       ├── employee-dashboard.js        # Employee Charts & Table Interactions
│       └── finance-dashboard.js         # Finance Charts, Filters & Review Dialogs
│
├── ml/                                  # Machine Learning Module
│   ├── dataset/
│   │   └── reimbursement_data.csv       # Training & Evaluation Dataset (2,500 rows)
│   ├── saved_models/                    # Persisted Artifacts
│   │   ├── random_forest_reimbursement.joblib  # Trained Model Pipeline
│   │   └── pipeline_metadata.joblib            # Feature & Performance Metadata
│   ├── generate_dataset.py              # Synthetic Corporate Dataset Generator
│   ├── train_model.py                   # Pipeline Training Script (80/20 Stratified)
│   └── evaluate_model.py                # Test Set Evaluation & Confusion Matrix
│
├── notebooks/
│   └── ml_reimbursement_risk_model.ipynb # Jupyter Notebook with EDA, Training & Plots
│
├── docs/
│   ├── PROJECT_DOCUMENTATION.md         # Detailed System Architecture & Design Spec
│   └── DEMO_VIDEO_SCRIPT.md             # 5-10 Minute Demonstration Script
│
├── scripts/
│   ├── init_db.py                       # MongoDB Collections & Indexes Initializer
│   ├── seed_db.py                       # Demo Users & Default Expense Categories Seeder
│   └── audit_database.py                # MongoDB Collections, Counts & Index Inspector
│
├── tests/                               # Automated Test Suite (pytest)
│   ├── conftest.py                      # Test Client & JWT Auth Fixtures
│   ├── test_auth.py                     # Authentication & Hashing Tests (9 tests)
│   ├── test_permissions.py              # RBAC & Forbidden Access Tests (5 tests)
│   ├── test_reimbursements.py           # Claim Creation, Validation & Upload (8 tests)
│   ├── test_prediction.py               # ML Random Forest Inference Tests (4 tests)
│   └── test_genai.py                    # Prompting, JSON Parsing & Mock LLM (4 tests)
│
├── uploads/                             # Protected Storage for Uploaded Bills
├── .env.example                         # Environment Variables Template
├── .env                                 # Active Configuration File
├── .gitignore                           # Git Exclusion Rules
├── requirements.txt                     # Python Package Dependencies
├── run.py                               # Server Startup Entry Point
└── README.md                            # Complete Project Guide
```

---

## 8. REST API Reference

### Authentication Endpoints
- `POST /api/auth/register` — Register a new employee account.
- `POST /api/auth/login` — Sign in and obtain JWT access token.
- `POST /api/auth/logout` — Invalidate client session.
- `GET /api/auth/me` — Retrieve profile of currently authenticated user.

### Employee Reimbursements
- `POST /api/reimbursements` — Submit a reimbursement claim (auto-triggers ML prediction and AI summary).
- `GET /api/reimbursements/my` — List all claims submitted by the authenticated employee.
- `GET /api/reimbursements/<id>` — Retrieve full details, AI observations, and audit log.
- `POST /api/reimbursements/<id>/upload` — Upload bill attachment (recalibrates ML risk in real time).
- `GET /api/reimbursements/<id>/bill` — Securely view/stream uploaded receipt.
- `GET /api/reimbursements/<id>/prediction` — Re-compute or fetch ML risk score.
- `POST /api/reimbursements/<id>/summary` — Re-generate Generative AI insights.

### Finance Administration (Admin Role Required)
- `GET /api/admin/reimbursements` — Filter all enterprise claims (status, employee, date, amount, risk).
- `GET /api/admin/reimbursements/<id>` — Detailed audit dossier with receipt and employee history.
- `POST /api/admin/reimbursements/<id>/approve` — Sanction claim with optional disbursement notes.
- `POST /api/admin/reimbursements/<id>/reject` — Reject claim (requires mandatory rejection reason).
- `GET /api/admin/analytics` — Enterprise metrics, high-risk alert list, and chart data.
- `GET /api/admin/employees` — List all employees for filter dropdowns.

### Category Management
- `GET /api/categories` — List active expense categories.
- `POST /api/admin/categories` — Create a new expense category.
- `PUT /api/admin/categories/<id>` — Update category name, description, or toggle active status.

---

## 9. Setup and Local Installation

### Prerequisites
- Windows 11 (or macOS / Linux).
- Python 3.10+ (tested on Python 3.13).
- MongoDB Atlas Cluster URI (or local MongoDB 6.0+ on port 27017).

### Step 1: Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` and configure your MongoDB Atlas credentials:
```ini
# MongoDB Atlas Database Configuration
MONGO_URI=mongodb+srv://<USERNAME>:<PASSWORD>@cluster0.gse3wum.mongodb.net/reimbursement_db?retryWrites=true&w=majority
MONGO_DB_NAME=reimbursement_db

# Security & Sessions
SECRET_KEY=your_secure_random_flask_secret_key
JWT_SECRET=your_jwt_signing_secret_key

# Generative AI (Optional, heuristic engine fallback provided)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
```

---

## 10. Running the Application

### 1. Initialize MongoDB Collections & Indexes
Connects to MongoDB, validates connectivity via `ping`, and creates collections and required indexes:
```bash
python scripts/init_db.py
```

### 2. Seed Default Expense Categories & Demo Accounts
Populates baseline categories and demo accounts (Admin and Employees) idempotently:
```bash
python scripts/seed_db.py
```

### 3. Verify Database State (Optional)
```bash
python scripts/audit_database.py
```

### 3. Generate ML Dataset & Train Random Forest Model
```bash
# Generate synthetic dataset (2,500 records)
python ml/generate_dataset.py

# Train Random Forest Pipeline and save joblib models
python ml/train_model.py

# Evaluate test metrics and display confusion matrix
python ml/evaluate_model.py
```

### 4. Start the Application Server
```bash
python run.py
```
Open your web browser and navigate to:
**`http://localhost:5000`**

---

## 11. Pre-Seeded Demo Accounts

| Role | Email | Password | Department |
| :--- | :--- | :--- | :--- |
| **Finance Admin** | `admin@company.com` | `Password@123` | Finance & Accounts |
| **Employee 1** | `john.doe@company.com` | `Password@123` | Engineering |
| **Employee 2** | `jane.smith@company.com` | `Password@123` | Marketing |
| **Employee 3** | `alex.kumar@company.com` | `Password@123` | Sales & BD |

*Tip:* The login page includes **one-click quick login buttons** to instantly sign in as either Finance Admin or Employee.

---

## 12. Running Automated Tests

Run the complete 30-test suite using pytest:
```bash
python -m pytest -v
```

All 30 tests run against mocked external services, requiring zero paid API keys and executing in under 6 seconds.

---

## 13. Deliverables & Documentation

- **Source Code:** Complete modular Python Flask application and vanilla JS frontend.
- **Trained Model:** Persisted at `ml/saved_models/random_forest_reimbursement.joblib`.
- **Dataset:** Available at `ml/dataset/reimbursement_data.csv`.
- **Jupyter Notebook:** `notebooks/ml_reimbursement_risk_model.ipynb` with complete preprocessing, training, feature importance plots, and confusion matrix.
- **Detailed System Specification:** `docs/PROJECT_DOCUMENTATION.md`.
- **Demo Video Script:** `docs/DEMO_VIDEO_SCRIPT.md` (complete 5–10 minute step-by-step narration).

---

## 14. Known Limitations

1. **Synthetic Training Data:** While statistically modeled on enterprise policy thresholds and distributions, the dataset is synthetic and demonstrates algorithmic capability rather than real-world audited corporate records.
2. **Synchronous File Storage:** File uploads are stored on local disk in `uploads/`. For enterprise multi-server deployments, a cloud object store (such as Amazon S3 or Google Cloud Storage) is recommended.
3. **Receipt OCR:** Current document validation checks MIME types and magic numbers. Integrating OCR (e.g., Tesseract or Google Cloud Document AI) could automatically extract merchant names and itemized totals from images.

