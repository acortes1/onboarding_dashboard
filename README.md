# Onboarding Performance Dashboard 🌟

## Description

This Streamlit web application provides an interactive, password-protected dashboard to visualize and analyze onboarding performance metrics. It dynamically loads data in near real-time from a specified Google Sheet (configured via secrets) and features a custom "Black, White, and Gold" theme for a polished user experience.

## Key Features

* **Password Protected:** Basic access key protection for the application.
* **Dynamic Data Loading:** Securely connects to a Google Sheet using the Google Sheets API, with data source details managed via Streamlit secrets.
* **Custom Theme:** "Black, White, and Gold" theme applied for a professional look and feel.
* **MTD (Month-to-Date) Metrics:**
    * Total Onboardings MTD
    * Overall Success Rate MTD
    * Average Rep Score MTD
    * Average Days to Confirmation MTD
* **Filtered Data Overview:** Displays key metrics calculated for the currently filtered dataset.
* **Interactive Filters:**
    * Filter data by Onboarding Date range.
    * Filter by Representative Name.
    * Filter by Onboarding Status.
    * Filter by Client Sentiment.
* **Data Sorting:** The main data table is sorted by Delivery Date (ascending).
* **Visualizations (Powered by Plotly Express):**
    * Onboarding Status Distribution (Bar Chart)
    * Client Sentiment Breakdown (Pie Chart)
    * Onboardings by Representative (Bar Chart)
    * Checklist Item Completion Rates (Horizontal Bar Chart)
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
* A Google Sheet containing the onboarding data.

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

4.  **Configure Streamlit Secrets for Local Development:**
    * **Create Secrets File:** Create a file named `secrets.toml` inside a `.streamlit` directory in your project root (i.e., `onboarding_dashboard/.streamlit/secrets.toml`).
    * **Google Sheets API Setup:**
        * In your GCP project, ensure "Google Drive API" and "Google Sheets API" are enabled.
        * Create a service account in GCP and download its JSON key file.
        * Populate the `[gcp_service_account]` section in your `.streamlit/secrets.toml` file with the contents of the downloaded JSON key. See the example TOML structure below.
    * **Data Source Configuration:**
        * In `.streamlit/secrets.toml`, add your Google Sheet URL/ID/Name and the specific Worksheet Name:
            ```toml
            GOOGLE_SHEET_URL_OR_NAME = "your_google_sheet_url_or_id_or_title"
            GOOGLE_WORKSHEET_NAME = "your_worksheet_name" # e.g., Sheet1
            ```
    * **Application Access Key:**
        * In `.streamlit/secrets.toml`, set the password and hint for the app:
            ```toml
            APP_ACCESS_KEY = "your_chosen_password" # e.g., "92606"
            APP_ACCESS_HINT = "your_password_hint"  # e.g., "Zip Code @ HQ"
            ```
            *(Note: The `streamlit_app.py` is configured to bypass password locally if `APP_ACCESS_KEY` is not found in secrets, for easier development. Ensure it's set for deployed versions.)*
    * **Share Google Sheet:** Open your target Google Sheet and share it with the service account's email address (found in the `client_email` field of your service account credentials). Grant at least "Viewer" permissions.
    * **IMPORTANT - `.gitignore`:** Make absolutely sure that `.streamlit/secrets.toml` is listed in your `.gitignore` file to prevent accidentally committing this sensitive file to GitHub.
        ```gitignore
        # Example .gitignore entry
        .streamlit/secrets.toml
        google_credentials.json # If used as a very old local fallback, also ignore
        *.csv
        __pycache__/
        venv/
        *.pyc
        ```

5.  **Running the App Locally:**
    ```bash
    streamlit run streamlit_app.py
    ```
    The application will use the configurations defined in your `.streamlit/secrets.toml` file.

## Deployment to Streamlit Community Cloud

1.  **Push to GitHub:** Ensure all your latest code (including `streamlit_app.py`, `requirements.txt`, and any configuration like `.streamlit/config.toml` if you have one for themes) is committed and pushed to your GitHub repository. Your `.streamlit/secrets.toml` file should *not* be in the repository.

2.  **Deploy on Streamlit Community Cloud:**
    * Go to [share.streamlit.io](https://share.streamlit.io/).
    * Connect your GitHub account.
    * Click "New app" and select your repository, branch, and `streamlit_app.py` as the main file.

3.  **Configure Streamlit Secrets on Streamlit Community Cloud:**
    * In your app's settings on Streamlit Community Cloud, navigate to the "Secrets" section.
    * Add all the necessary secrets in TOML format. This includes the `[gcp_service_account]` details, `GOOGLE_SHEET_URL_OR_NAME`, `GOOGLE_WORKSHEET_NAME`, `APP_ACCESS_KEY`, and `APP_ACCESS_HINT`.
    * **Example TOML structure for secrets:**
        ```toml
        [gcp_service_account]
        type = "service_account"
        project_id = "your-gcp-project-id"
        private_key_id = "your-private-key-id"
        private_key = """-----BEGIN PRIVATE KEY-----\nYOUR_MULTI_LINE_PRIVATE_KEY_HERE_WITH_NEWLINES_PRESERVED\n-----END PRIVATE KEY-----\n"""
        client_email = "your-service-account-email@your-gcp-project-id.iam.gserviceaccount.com"
        client_id = "your-client-id"
        auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)"
        token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"
        auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)"
        client_x509_cert_url = "YOUR_CLIENT_X509_CERT_URL_HERE"
        universe_domain = "googleapis.com" # If present in your JSON

        # Data Source Configuration
        GOOGLE_SHEET_URL_OR_NAME = "your_actual_google_sheet_url_or_id_or_title"
        GOOGLE_WORKSHEET_NAME = "your_actual_worksheet_name"

        # Application Access Control
        APP_ACCESS_KEY = "your_actual_password"
        APP_ACCESS_HINT = "your_actual_password_hint"
        ```
    * Save the secrets. Your app should then be able to authenticate, check the access key, and fetch data.

## Project Structure

onboarding_dashboard/
│
├── .streamlit/
│   ├── secrets.toml      # (For local development ONLY, MUST be in .gitignore) Contains API keys, sheet URL, password
│   └── config.toml       # Optional: Streamlit theme configuration (if you have one)
├── streamlit_app.py      # Main Streamlit application script
├── requirements.txt      # Python dependencies
└── README.md             # This file