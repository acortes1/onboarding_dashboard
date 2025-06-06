# Onboarding Performance Dashboard 🌟 (v4.6.7)

## Description

This Streamlit web application provides an interactive dashboard to visualize and analyze onboarding performance metrics. It now features **Google Single Sign-On (SSO)** for secure access, dynamically loads data in near real-time from a specified Google Sheet (configured via secrets), and uses a custom theme for a polished user experience.

## Key Features

* **Secure Access:**
    * **Google SSO Login:** Users must log in with their Google account.
    * **(Optional) Domain Restriction:** Can be configured (via secrets) to only allow users from a specific Google Workspace domain.
* **Dynamic Data Loading:** Securely connects to a Google Sheet using the Google Sheets API, with data source details managed via Streamlit secrets.
* **Custom Theme & CSS:** Enhanced styling for a professional look and feel, adaptable to light/dark modes.
* **MTD (Month-to-Date) Metrics:**
    * Total Onboardings MTD (with comparison to the previous month).
    * Overall Success Rate MTD.
    * Average Rep Score MTD.
    * Average Days to Confirmation MTD.
* **Global Search:** Quickly find records by License Number or Store Name (overrides filters).
* **Interactive Filters:**
    * Filter data by Onboarding Date range (with MTD/YTD/ALL shortcuts).
    * Filter by Representative Name.
    * Filter by Onboarding Status.
    * Filter by Client Sentiment.
* **Data Table & Details:**
    * Displays filtered data in a sortable, styled table.
    * Select a record to view its full details, including call summary and key requirement checks.
    * Download filtered results as a CSV.
* **Visualizations (Powered by Plotly Express):**
    * Onboarding Status Distribution (Bar Chart).
    * Client Sentiment Breakdown (Pie Chart).
    * Onboardings by Representative (Bar Chart).
    * Checklist Item Completion Rates (Horizontal Bar Chart).
    * Onboardings Over Time (Line Chart).
    * Days to Confirmation Distribution (Histogram).
* **Data Refresh:** A button in the sidebar allows manual refreshing of data from the Google Sheet.

## Technologies Used

* Python 3.x
* Streamlit (with Google SSO integration)
* Pandas
* Plotly Express
* gspread (for Google Sheets API interaction)
* Google Cloud Service Account (for authentication with Google APIs)

## Setup and Local Development

### Prerequisites

* Python 3.8 or higher.
* Access to a Google Cloud Platform (GCP) project.
* A Google Sheet containing the onboarding data.
* A Google Account (for logging in).

### Steps

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd onboarding_dashboard
    ```

2.  **Create and Activate a Virtual Environment** (Recommended):
    ```bash
    python -m venv venv
    # On macOS/Linux:
    source venv/bin/activate
    # On Windows:
    # venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Streamlit Secrets for Local Development:**
    * **Create Secrets File:** Create `.streamlit/secrets.toml` in your project root.
    * **Google Sheets API Setup:**
        * Enable "Google Drive API" and "Google Sheets API" in GCP.
        * Create a service account, download its JSON key.
        * Populate `[gcp_service_account]` in `secrets.toml` with the JSON contents.
    * **Data Source:** Add `GOOGLE_SHEET_URL_OR_NAME` and `GOOGLE_WORKSHEET_NAME`.
    * **(Optional) Domain Restriction:** Add `ALLOWED_DOMAIN = "yourdomain.com"` if needed.
    * **Share Google Sheet:** Share the sheet with the service account's email (Viewer or Editor).
    * **`.gitignore`:** Ensure `.streamlit/secrets.toml` is in your `.gitignore`!

5.  **Running the App Locally:**
    ```bash
    streamlit run streamlit_app.py
    ```
    You will be prompted to log in with your Google Account when you open the app.

## Deployment to Streamlit Community Cloud

1.  **Push to GitHub:** Ensure all code (except `secrets.toml`) is pushed.

2.  **Deploy on Streamlit Community Cloud:**
    * Go to [share.streamlit.io](https://share.streamlit.io/).
    * Connect GitHub, select your repo, branch, and `streamlit_app.py`.

3.  **Enable Google SSO on Streamlit Community Cloud:**
    * In your app's settings, go to the "Authentication" section.
    * Enable "Google Authentication". This handles the login process.

4.  **Configure Streamlit Secrets on Streamlit Community Cloud:**
    * Go to the "Secrets" section.
    * Add all necessary secrets in TOML format, just like your local file:
        * `[gcp_service_account]` details.
        * `GOOGLE_SHEET_URL_OR_NAME`.
        * `GOOGLE_WORKSHEET_NAME`.
        * `(Optional) ALLOWED_DOMAIN`.
    * Save the secrets. Your app should now be live and secure!

## Project Structure
onboarding_dashboard/
│
├── .streamlit/
│   ├── secrets.toml      # (Local ONLY, MUST be in .gitignore)
│   └── config.toml       # Optional: Streamlit theme config
├── .devcontainer/        # Optional: For development containers
│   └── devcontainer.json
├── streamlit_app.py      # Main application script
├── requirements.txt      # Python dependencies
└── README.md             # This file