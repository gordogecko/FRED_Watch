import streamlit as st
import pandas as pd
import requests
from fredapi import Fred
import datetime
from concurrent.futures import ThreadPoolExecutor

# --- 1. Configuration & Setup ---
# Fetch the active FRED API key from Streamlit secrets
FRED_API_KEY = st.secrets["FRED_API_KEY"]
fred = Fred(api_key=FRED_API_KEY)

class HFMApiClient:
    def __init__(self, base_url="https://data.financialresearch.gov/hf/v1"):
        self.base_url = base_url

    @st.cache_data(ttl=3600)
    def get_all_mnemonics(_self):
        url = f"{_self.base_url}/metadata/mnemonics/"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Error fetching mnemonics: {e}")
        return []

    @st.cache_data(ttl=3600)
    def get_multifull_data(_self, mnemonics):
        url = f"{_self.base_url}/series/multifull/"
        params = {'mnemonics': ",".join(mnemonics)}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Error fetching HFM data: {e}")
        return None

# --- 2. Data Fetching & Helper Functions ---

@st.cache_data(ttl=86400)
def get_series_data(series_codes):
    """Generic fetcher to reduce redundancy and improve performance."""
    data = {}
    def fetch_series(name, code):
        try:
            return name, fred.get_series(code)
        except Exception:
            return name, None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_series, name, code): name for name, code in series_codes.items()}
        for future in futures:
            name, series = future.result()
            if series is not None:
                data[name] = series
    
    df = pd.DataFrame(data)
    return df.ffill().loc['2015-01-01':]

def get_macro_codes():
    return {
        'M1 Money Supply': 'M1SL', 'M2 Money Supply': 'M2SL', 'Fed Balance Sheet': 'WALCL',
        'Foreign Holdings of US Treasuries': 'FORTREASPOS99996',
        '1-Month Treasury Yield': 'DGS1MO', '3-Month Treasury Yield': 'DGS3MO',
        '6-Month Treasury Yield': 'DGS6MO', '1-Year Treasury Yield': 'DGS1',
        '2-Year Treasury Yield': 'DGS2', '3-Year Treasury Yield': 'DGS3',
        '5-Year Treasury Yield': 'DGS5', '7-Year Treasury Yield': 'DGS7',
        '10-Year Treasury Yield': 'DGS10', '20-Year Treasury Yield': 'DGS20',
        '30-Year Treasury Yield': 'DGS30',
        'Effective Federal Funds Rate': 'EFFR', 'Overnight Bank Funding Rate': 'OBFR',
        'Euro Short-Term Rate': 'ECBESTRVOLWGTTRMDMNRT',
        'Risk-ON Risk-Off Index': 'KCRORO', 'KCRORO: Equities': 'KCROROE',
        'KCRORO: Gold and USD': 'KCROROG', 'KCRORO: Spreads': 'KCROROS',
        'KCRORO: Liquidity': 'KCROROL',
        'Economic Policy Uncertainty': 'USEPUINDXM', 'Nikkei 225': 'NIKKEI225'
    }

def get_corp_bond_codes():
    return {
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

def filter_by_date(df, start_date, end_date):
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        df.index = pd.to_datetime(df.index)
    mask = (df.index.date >= start_date) & (df.index.date <= end_date)
    return df.loc[mask]

# --- 3. Dashboard Layout ---

def main():
    st.set_page_config(page_title="Integrated Financial Dashboard", layout="wide")
    st.title("Financial Research & Market Vibe Dashboard")

    col1, col2 = st.columns([1, 3])
    with col1:
        detailed_view = st.toggle("🔍 Enable Detailed Date View")
    
    start_date, end_date = None, None
    if detailed_view:
        with col2:
            today = datetime.date.today()
            five_yrs_ago = today.replace(year=today.year - 5)
            date_range = st.date_input("Select Date Range", value=(five_yrs_ago, today))
            if len(date_range) == 2:
                start_date, end_date = date_range

    tab1, tab2, tab3, tab4 = st.tabs(["Macro & Market Trends", "Hedge Fund API Data", "Advanced Indicators", "Corporate Bonds"])

    # Load data
    with st.spinner("Loading market data..."):
        macro_df = get_series_data(get_macro_codes())
        corp_df = get_series_data(get_corp_bond_codes())

    def apply_filter(df):
        return filter_by_date(df.copy(), start_date, end_date) if detailed_view and start_date and end_date else df.copy()

    with tab1:
        display_df = apply_filter(macro_df)
        st.subheader("M1 & M2 Money Supply")
        st.line_chart(display_df[['M1 Money Supply', 'M2 Money Supply']].dropna(how='all'))
        
        st.subheader("Fed Balance Sheet & Foreign Holdings")
        st.line_chart(display_df[['Fed Balance Sheet', 'Foreign Holdings of US Treasuries']].dropna(how='all'))
        
        st.subheader("U.S. Treasury Yield Curve")
        yield_cols = [c for c in get_macro_codes().keys() if 'Yield' in c and c in display_df.columns]
        st.line_chart(display_df[yield_cols].dropna(how='all'))

    with tab2:
        client = HFMApiClient()
        mnemonics = client.get_all_mnemonics()
        if mnemonics:
            batch = mnemonics[:100]
            hfm_data = client.get_multifull_data(tuple(batch))
            if hfm_data:
                selected = st.selectbox("Select Mnemonic", options=list(hfm_data.keys()), key="hfm_selector")
                raw_data = hfm_data.get(selected, {}).get("timeseries", {}).get("aggregation", [])
                if raw_data:
                    df = pd.DataFrame(raw_data, columns=["Date", "Value"]).set_index(pd.to_datetime([x[0] for x in raw_data]))
                    df = df.drop(columns=["Date"])
                    df = apply_filter(df)
                    st.line_chart(df)
    
    with tab3:
        display_df = apply_filter(macro_df)
        st.subheader("Monetary Policy Rates")
        st.line_chart(display_df[['Effective Federal Funds Rate', 'Overnight Bank Funding Rate', 'Euro Short-Term Rate']].dropna(how='all'))
        
        # Renaming to avoid Altair/Vega-Lite parsing issues with colons
        display_df = display_df.rename(columns={
            'KCRORO: Gold and USD': 'KCRORO_Gold_USD', 
            'KCRORO: Liquidity': 'KCRORO_Liquidity',
            'KCRORO: Equities': 'KCRORO_Equities', 
            'KCRORO: Spreads': 'KCRORO_Spreads'
        })
        
        st.subheader("Risk-ON Risk-Off Index")
        st.line_chart(display_df[['Risk-ON Risk-Off Index']].dropna())
        st.subheader("KCRORO: Gold and USD")
        st.line_chart(display_df[['KCRORO_Gold_USD']].dropna())
        st.subheader("KCRORO: Liquidity")
        st.line_chart(display_df[['KCRORO_Liquidity']].dropna())
        st.subheader("KCRORO: Equities")
        st.line_chart(display_df[['KCRORO_Equities']].dropna())
        st.subheader("KCRORO: Spreads")
        st.line_chart(display_df[['KCRORO_Spreads']].dropna())
        
    with tab4:
        display_corp = apply_filter(corp_df)
        selected_bond = st.selectbox("Select Corporate Bond", options=list(display_corp.columns), key="corp_bond_selector")
        st.line_chart(display_corp[selected_bond].dropna())

if __name__ == "__main__":
    main()
