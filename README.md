# Financial Research & Market Vibe Dashboard

An interactive dashboard built with Streamlit that aggregates macro-economic data from the FRED API and financial research metrics.

## Features
*   **Macro & Market Trends**: Tracks money supply, Fed balance sheet, and U.S. Treasury yield curves.
*   **Hedge Fund Data**: Explores data from the HFM API.
*   **Advanced Indicators**: Monitors monetary policy rates, Risk-ON/Risk-Off (KCRORO) metrics, and Economic Policy Uncertainty.
*   **Corporate Bonds**: Interactive explorer for various Moody's and ICE BofA corporate bond yields.

## Setup Requirements
1. **FRED API Key**: You must obtain a free API key from the [FRED API website](https://fred.stlouisfed.org/docs/api/api_key.html).
2. **Environment**: Ensure you have Python 3.9+ installed.

## Set up your API key:
Create a .streamlit/secrets.toml file in your project root.
Add your key:
FRED_API_KEY = "your_actual_api_key_here"

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/gordogecko/FRED_Watch.git
   cd your-repo-name

## Install dependencies
pip install -r requirements.txt

## Running the App
streamlit run fredWatch.py






