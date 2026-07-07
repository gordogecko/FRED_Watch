import streamlit as st
import pandas as pd
import requests
from fredapi import Fred
import datetime

# --- 1. Configuration & Setup ---
# Fetch the active FRED API key from Streamlit secrets
FRED_API_KEY = st.secrets["FRED_API_KEY"]
fred = Fred(api_key=FRED_API_KEY)


class HFMApiClient:
    def __init__(self, base_url="https://data.financialresearch.gov/hf/v1"):
        self.base_url = base_url

    def get_all_mnemonics(self):
        url = f"{self.base_url}/metadata/mnemonics/"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return []

    def get_multifull_data(self, mnemonics):
        url = f"{self.base_url}/series/multifull/"
        params = {'mnemonics': ",".join(mnemonics)}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return None


# --- 2. Data Fetching & Helper Functions ---

@st.cache_data
def get_macro_data():
    series_codes = {
        # Base Macro Metrics
        'M1 Money Supply': 'M1SL',
        'M2 Money Supply': 'M2SL',
        'Fed Balance Sheet': 'WALCL',
        'Foreign Holdings of US Treasuries': 'FORTREASPOS99996',

        # Treasury Yield Curve
        '1-Month Treasury Yield': 'DGS1MO',
        '3-Month Treasury Yield': 'DGS3MO',
        '6-Month Treasury Yield': 'DGS6MO',
        '1-Year Treasury Yield': 'DGS1',
        '2-Year Treasury Yield': 'DGS2',
        '3-Year Treasury Yield': 'DGS3',
        '5-Year Treasury Yield': 'DGS5',
        '7-Year Treasury Yield': 'DGS7',
        '10-Year Treasury Yield': 'DGS10',
        '20-Year Treasury Yield': 'DGS20',
        '30-Year Treasury Yield': 'DGS30',

        # New Add-ons: Monetary Policy
        'Effective Federal Funds Rate': 'EFFR',
        'Overnight Bank Funding Rate': 'OBFR',
        'Euro Short-Term Rate': 'ECBESTRVOLWGTTRMDMNRT',

        # New Add-ons: Risk-ON Risk-Off (KCRORO)
        'Risk-ON Risk-Off Index': 'KCRORO',
        'KCRORO: Equities': 'KCROROE',
        'KCRORO: Gold and USD': 'KCROROG',
        'KCRORO: Spreads': 'KCROROS',
        'KCRORO: Liquidity': 'KCROROL',

        # New Add-ons: Global & Uncertainty
        'Economic Policy Uncertainty': 'USEPUINDXM',
        'Nikkei 225': 'NIKKEI225'
    }

    from concurrent.futures import ThreadPoolExecutor

    data = {}
    def fetch_series(name, code):
        try:
            return name, fred.get_series(code)
        except Exception:
            return name, None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_series, name, code) for name, code in series_codes.items()]
        for future in futures:
            name, series = future.result()
            if series is not None:
                data[name] = series

    df = pd.DataFrame(data)
    # Forward-fill ensures different reporting frequencies plot seamlessly together
    return df.ffill().loc['2015-01-01':]


@st.cache_data
def get_hfm_data():
    client = HFMApiClient()
    mnemonics = client.get_all_mnemonics()
    # Limit to first 100 for performance
    batch = mnemonics[:100]
    return client.get_multifull_data(batch)


@st.cache_data
def get_corp_bond_data():
    """Fetches key datasets from FRED's Corporate Bonds Category (32348)"""
    corp_bond_codes = {
        "Moody's Seasoned Aaa Corporate Bond Yield": "AAA",
        "Moody's Seasoned Baa Corporate Bond Yield": "BAA",
        "ICE BofA AAA US Corporate Index Effective Yield": "BAMLC0A1CAAAEY",
        "ICE BofA AA US Corporate Index Effective Yield": "BAMLC0A2CAAEY",
        "ICE BofA A US Corporate Index Effective Yield": "BAMLC0A3CAEY",
        "ICE BofA BBB US Corporate Index Effective Yield": "BAMLC0A4CBBBEY",
        "ICE BofA BB US High Yield Index Effective Yield": "BAMLH0A1HYBBEY",
        "ICE BofA Single-B US High Yield Index Effective Yield": "BAMLH0A2HYBEY",
        "ICE BofA CCC & Lower US High Yield Index Effective Yield": "BAMLH0A3HYCEY",
        "1-Year HQM Corporate Bond Spot Rate": "HQMCB1YR",
        "5-Year HQM Corporate Bond Spot Rate": "HQMCB5YR",
        "10-Year HQM Corporate Bond Spot Rate": "HQMCB10YR",
        "20-Year HQM Corporate Bond Spot Rate": "HQMCB20YR",
        "30-Year HQM Corporate Bond Spot Rate": "HQMCB30YR",
    }

    from concurrent.futures import ThreadPoolExecutor

    data = {}
    def fetch_series(name, code):
        try:
            return name, fred.get_series(code)
        except Exception:
            return name, None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_series, name, code) for name, code in corp_bond_codes.items()]
        for future in futures:
            name, series = future.result()
            if series is not None:
                data[name] = series

    df = pd.DataFrame(data)
    return df.ffill().loc['2015-01-01':]


def filter_by_date(df, start_date, end_date):
    """Helper function to filter dataframes by selected date range."""
    # Ensure index is datetime for reliable comparison
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        df.index = pd.to_datetime(df.index)

    mask = (df.index.date >= start_date) & (df.index.date <= end_date)
    return df.loc[mask]


# --- 3. Dashboard Layout ---

def main():
    st.set_page_config(page_title="Integrated Financial Dashboard", layout="wide")
    st.title("Financial Research & Market Vibe Dashboard")

    # --- Global Detailed View & Date Picker ---
    st.markdown("---")
    col1, col2 = st.columns([1, 3])

    with col1:
        detailed_view = st.toggle("🔍 Enable Detailed Date View")

    start_date, end_date = None, None
    if detailed_view:
        with col2:
            today = datetime.date.today()
            five_yrs_ago = today.replace(year=today.year - 5)
            date_range = st.date_input("Select Date Range for all charts", value=(five_yrs_ago, today))

            # Ensure the user has selected both start and end dates before applying
            if len(date_range) == 2:
                start_date, end_date = date_range

    st.markdown("---")

    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Macro & Market Trends", "Hedge Fund API Data", "Advanced Indicators (Add-Ons)", "Corporate Bonds"])

    macro_df = get_macro_data()

    # Apply date filter to macro data if toggle is active
    if not macro_df.empty and detailed_view and start_date and end_date:
        display_macro_df = filter_by_date(macro_df.copy(), start_date, end_date)
    else:
        display_macro_df = macro_df.copy()

    # --- Tab 1: Base Macro Data ---
    with tab1:
        st.header("Macro & Micro Market Trends")

        if not display_macro_df.empty:
            st.subheader("M1 & M2 Money Supply")
            st.line_chart(display_macro_df[['M1 Money Supply', 'M2 Money Supply']])

            st.subheader("Federal Reserve Balance Sheet & Foreign Holdings")
            st.line_chart(display_macro_df[['Fed Balance Sheet', 'Foreign Holdings of US Treasuries']])

            # Dedicated Treasury Yield Curve Chart
            st.subheader("U.S. Treasury Yield Curve")
            yield_columns = [
                '1-Month Treasury Yield', '3-Month Treasury Yield', '6-Month Treasury Yield',
                '1-Year Treasury Yield', '2-Year Treasury Yield', '3-Year Treasury Yield',
                '5-Year Treasury Yield', '7-Year Treasury Yield', '10-Year Treasury Yield',
                '20-Year Treasury Yield', '30-Year Treasury Yield'
            ]

            # Validate which columns successfully fetched to prevent chart rendering errors
            valid_yield_columns = [col for col in yield_columns if col in display_macro_df.columns]

            if valid_yield_columns:
                st.line_chart(display_macro_df[valid_yield_columns].dropna(how='all'))
            else:
                st.warning("Treasury yield data is currently unavailable.")

        else:
            st.error("Unable to load Macro data, or no data available for the selected date range.")

    # --- Tab 2: HFM Data ---
    with tab2:
        st.header("Hedge Fund Research Data Explorer")
        with st.spinner("Fetching data from HFM API..."):
            hfm_data = get_hfm_data()

        if hfm_data:
            selected_mnemonic = st.selectbox(
                "Select a Mnemonic to Visualize",
                options=list(hfm_data.keys()),
                key="hfm_selector"
            )

            details = hfm_data.get(selected_mnemonic, {})
            raw_data = details.get("timeseries", {}).get("aggregation", [])

            if raw_data:
                df = pd.DataFrame(raw_data, columns=["Date", "Value"])
                df["Date"] = pd.to_datetime(df["Date"])
                df = df.set_index("Date")

                # Apply date filter to HFM data if toggle is active
                if detailed_view and start_date and end_date:
                    df = filter_by_date(df, start_date, end_date)

                st.subheader(f"Trend for: {selected_mnemonic}")

                if not df.empty:
                    st.line_chart(df)
                    with st.expander("View Raw Data"):
                        st.dataframe(df)
                else:
                    st.warning("No data available for this metric within the selected date range.")
            else:
                st.error("No aggregation data found for this selection.")
        else:
            st.error("Failed to load HFM data.")

    # --- Tab 3: New Add-On Data ---
    with tab3:
        st.header("Advanced Market Indicators")

        if not display_macro_df.empty:

            st.subheader("Monetary Policy Rates")
            st.line_chart(display_macro_df[[
                'Effective Federal Funds Rate',
                'Overnight Bank Funding Rate',
                'Euro Short-Term Rate'
            ]].dropna(how='all'))

            # Renaming columns to remove colons to prevent Vega-Lite encoding errors
            display_macro_df = display_macro_df.rename(columns={
                'KCRORO: Gold and USD': 'KCRORO_Gold_USD',
                'KCRORO: Liquidity': 'KCRORO_Liquidity',
                'KCRORO: Equities': 'KCRORO_Equities',
                'KCRORO: Spreads': 'KCRORO_Spreads'
            })

            st.markdown("---")
            st.subheader("Risk-ON Risk-Off (KCRORO) Metrics")

            kc_col1, kc_col2 = st.columns(2)

            with kc_col1:
                st.write("**Overall Risk-ON Risk-Off Index**")
                st.line_chart(display_macro_df['Risk-ON Risk-Off Index'].dropna())

                st.write("**KCRORO: Gold and USD**")
                st.line_chart(display_macro_df['KCRORO_Gold_USD'].dropna())

                st.write("**KCRORO: Liquidity**")
                st.line_chart(display_macro_df['KCRORO_Liquidity'].dropna())

            with kc_col2:
                st.write("**KCRORO: Equities**")
                st.line_chart(display_macro_df['KCRORO_Equities'].dropna())

                st.write("**KCRORO: Spreads**")
                st.line_chart(display_macro_df['KCRORO_Spreads'].dropna())

            st.markdown("---")
            st.subheader("Global Macro & Uncertainty")
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Economic Policy Uncertainty**")
                st.line_chart(display_macro_df['Economic Policy Uncertainty'].dropna())

            with col2:
                st.write("**Nikkei 225**")
                st.line_chart(display_macro_df['Nikkei 225'].dropna())

        else:
            st.error("Unable to load Advanced Indicator data or no data in range.")

    # --- Tab 4: Corporate Bonds ---
    with tab4:
        st.header("Corporate Bonds Data Explorer")
        with st.spinner("Fetching Corporate Bonds Data..."):
            corp_df = get_corp_bond_data()

        if not corp_df.empty:
            # Apply date filter to corporate bonds data if toggle is active
            if detailed_view and start_date and end_date:
                display_corp_df = filter_by_date(corp_df.copy(), start_date, end_date)
            else:
                display_corp_df = corp_df.copy()

            selected_bond = st.selectbox(
                "Select Corporate Bond Dataset to Visualize",
                options=list(display_corp_df.columns),
                key="corp_bond_selector"
            )

            st.subheader(f"Trend for: {selected_bond}")

            # Ensure the selected column has data to plot
            if not display_corp_df[selected_bond].dropna().empty:
                st.line_chart(display_corp_df[selected_bond].dropna())

                with st.expander("View Raw Data"):
                    st.dataframe(display_corp_df[selected_bond].dropna())
            else:
                st.warning("No data available for this corporate bond within the selected date range.")
        else:
            st.error("Failed to load Corporate Bonds data.")


if __name__ == "__main__":
    main()
