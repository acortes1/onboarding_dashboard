# Onboarding Performance Dashboard 🌟

## Description

This Streamlit web application provides an interactive dashboard to visualize and analyze onboarding performance metrics. It dynamically loads data in near real-time from a specified Google Sheet, allowing for up-to-date insights. The dashboard features a custom "Black, White, and Gold" theme for a polished and visually appealing user experience.

## Key Features

* **Dynamic Data Loading:** Connects directly to a Google Sheet using the Google Sheets API for data sourcing.
* **Custom Theme:** "Black, White, and Gold" theme applied for a professional look and feel.
* **MTD (Month-to-Date) Metrics:**
    * Total Onboardings MTD
    * Overall Success Rate MTD
    * Average Rep Score MTD
    * Average Days to Confirmation MTD
* **Filtered Data Overview:** Displays the same set of key metrics calculated for the currently filtered dataset.
* **Interactive Filters:**
    * Filter data by Onboarding Date range (defaults to current Month-to-Date).
    * Filter by Representative Name.
    * Filter by Onboarding Status.
    * Filter by Client Sentiment.
* **Data Sorting:** The main data table is sorted by Delivery Date (ascending).
* **Visualizations (Powered by Plotly Express):**
    * Onboarding Status Distribution (Bar Chart)
    * Client Sentiment Breakdown (Pie Chart)
    * Onboardings by Representative (Bar Chart)
    * Checklist Item Completion Rates (Horizontal Bar Chart for boolean columns)
* **Data Refresh:** A button in the sidebar allows manual refreshing of data from the Google Sheet.

## Technologies Used

* Python 3.x
* Streamlit
* Pandas
* Plotly Express
* gspread (for Google Sheets API interaction)
* Google Cloud Service Account (for authentication with Google APIs)

## Setup and Local Development

### Prerequisites

* Python 3.8 or higher.
* Access to a Google Cloud Platform (GCP) project.
* A Google Sheet containing the onboarding data. The original data structure was based on `Onboarding_Confirmation_Log.xlsx - Sheet1.csv`.

### Steps

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd onboarding_dashboard 
    ```
    *(Replace `<your-repository-url>` with the actual URL of your GitHub repository.)*

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

4.  **Google Sheets API Setup (for Local Development):**
    * **Enable APIs:** In your GCP project, ensure "Google Drive API" and "Google Sheets API" are enabled.
    * **Create Service Account:** Create a service account in GCP and download its JSON key file.
    * **Credentials File:** Rename the downloaded JSON key file to `google_credentials.json` and place it in the root directory of this project.
    * **IMPORTANT - `.gitignore`:** Make absolutely sure that `google_credentials.json` is listed in your `.gitignore` file to prevent accidentally committing this sensitive file to GitHub.
        ```gitignore
        # Example .gitignore entry
        google_credentials.json
        *.csv
        __pycache__/
        # ... other ignores
        ```
    * **Share Google Sheet:** Open your target Google Sheet and share it with the service account's email address (found in the `client_email` field of your `google_credentials.json` file). Grant at least "Viewer" permissions.

5.  **Running the App Locally:**
    ```bash
    streamlit run streamlit_app.py
    ```
    The application is configured by default to use the Google Sheet at:
    `https://docs.google.com/spreadsheets/d/1hRtY8fXsVdgbn2midF0-y2HleEruasxldCtL3WVjWl0/edit?usp=sharing`
    and worksheet name `Sheet1`. Ensure your service account has access to this sheet.

## Deployment to Streamlit Community Cloud

1.  **Push to GitHub:** Ensure all your latest code (including `streamlit_app.py`, `requirements.txt`, and the `.streamlit/config.toml` file) is committed and pushed to your GitHub repository. Your `google_credentials.json` file should *not* be in the repository (it should be in `.gitignore`).

2.  **Deploy on Streamlit Community Cloud:**
    * Go to [share.streamlit.io](https://share.streamlit.io/).
    * Connect your GitHub account.
    * Click "New app" and select your repository, branch, and `streamlit_app.py` as the main file.

3.  **Configure Streamlit Secrets:**
    * In your app's settings on Streamlit Community Cloud, navigate to the "Secrets" section.
    * Add your Google Service Account JSON key's *content* in TOML format. The Python script expects these secrets under the `[gcp_service_account]` key.
    * **Example TOML structure for secrets:**
        ```toml
        [gcp_service_account]
        type = "service_account"
        project_id = "your-gcp-project-id"
        private_key_id = "your-private-key-id"
        private_key = """-----BEGIN PRIVATE KEY-----\nYOUR_MULTI_LINE_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"""
        client_email = "your-service-account-email@your-gcp-project-id.iam.gserviceaccount.com"
        client_id = "your-client-id"
        # ... include all other fields from your JSON key file
        auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)"
        token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"
        auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)"
        client_x509_cert_url = "YOUR_CLIENT_X509_CERT_URL_HERE"
        universe_domain = "googleapis.com" # If present in your JSON
        ```
    * Save the secrets. Your app should then be able to authenticate and fetch data from your Google Sheet.

## Project Structure
onboarding_dashboard/
│
├── .streamlit/
│   └── config.toml       # Streamlit theme configuration
├── streamlit_app.py      # Main Streamlit application script
├── requirements.txt      # Python dependencies
├── google_credentials.json # (For local development ONLY, MUST be in .gitignore)
└── README.md             # This file