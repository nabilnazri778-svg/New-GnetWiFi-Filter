import io
import re
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="G-NetWiFi Multi-Select RSSI Filter", layout="wide")

st.title("G-NetWiFi Pro Multi-Select RSSI Filter")
st.caption(
    "Upload the original G-NetWiFi .txt log. The app combines connected WiFi and scanned WiFi records, "
    "then filters by one or many SSIDs, BSSIDs, and FREQ values while keeping RSSI readings."
)

META_COLUMNS = [
    "Timestamp", "Longitude", "Latitude", "Speed", "Name", "Location", "Altitude", "Height", "Accuracy",
    "DataConnection_Type", "DataConnection_Info", "Filemark", "EVENT", "EVENTDETAILS",
]
CONNECTED_COLUMNS = ["SSID", "BSSID", "Frequency", "Channel", "RSSI", "LinkSpeed"]
SCAN_FIELDS = ["SSID", "BSSID", "FREQ", "CHAN", "SECURITY", "PSK", "RSSI", "BANDWIDTH"]


def normalise_colname(name: str) -> str:
    return str(name).strip().replace("\ufeff", "")


@st.cache_data(show_spinner=False)
def load_file(uploaded_name: str, raw_bytes: bytes) -> pd.DataFrame:
    suffix = Path(uploaded_name).suffix.lower()
    if suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(io.BytesIO(raw_bytes), dtype=str)
    else:
        # Original G-NetWiFi .txt is tab-separated.
        df = pd.read_csv(io.BytesIO(raw_bytes), sep="\t", dtype=str, engine="python")

    df.columns = [normalise_colname(c) for c in df.columns]
    df = df.dropna(how="all")
    unnamed_cols = [c for c in df.columns if str(c).startswith("Unnamed:")]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
    return df


def to_numeric_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def build_connected_table(df: pd.DataFrame) -> pd.DataFrame:
    if not {"SSID", "BSSID", "Frequency", "RSSI"}.issubset(set(df.columns)):
        return pd.DataFrame()

    meta = [c for c in META_COLUMNS if c in df.columns]
    keep = meta + [c for c in CONNECTED_COLUMNS if c in df.columns]
    connected = df[keep].copy()
    connected = connected.rename(columns={"Frequency": "FREQ", "Channel": "CHAN"})
    connected["Source"] = "Connected"
    connected["Slot"] = "Connected"
    connected = connected.dropna(subset=["SSID", "BSSID", "FREQ", "RSSI"], how="all")
    connected = connected[connected["SSID"].astype(str).str.strip().ne("")]
    connected = to_numeric_columns(connected, ["FREQ", "CHAN", "RSSI", "LinkSpeed"])
    return connected


def find_scan_indices(columns: list[str]) -> list[int]:
    indices = []
    for c in columns:
        m = re.fullmatch(r"SSID(\d+)", str(c))
        if m:
            indices.append(int(m.group(1)))
    return sorted(set(indices))


def build_scanned_table(df: pd.DataFrame) -> pd.DataFrame:
    indices = find_scan_indices(list(df.columns))
    if not indices:
        return pd.DataFrame()

    meta = [c for c in META_COLUMNS if c in df.columns]
    parts = []
    for i in indices:
        required = {f"SSID{i}", f"BSSID{i}", f"FREQ{i}", f"RSSI{i}"}
        if not required.issubset(set(df.columns)):
            continue

        col_map = {f"{field}{i}": field for field in SCAN_FIELDS if f"{field}{i}" in df.columns}
        temp = df[meta + list(col_map.keys())].copy()
        temp = temp.rename(columns=col_map)
        temp["Source"] = "Scanned"
        temp["Slot"] = f"Scan_{i}"
        temp = temp.dropna(subset=["SSID", "BSSID", "FREQ", "RSSI"], how="all")
        temp = temp[temp["SSID"].astype(str).str.strip().ne("")]
        parts.append(temp)

    if not parts:
        return pd.DataFrame()

    scanned = pd.concat(parts, ignore_index=True)
    scanned = to_numeric_columns(scanned, ["FREQ", "CHAN", "RSSI", "BANDWIDTH"])
    return scanned


def prepare_text_options(series: pd.Series) -> list[str]:
    values = series.dropna().astype(str).str.strip()
    values = values[values.ne("")]
    return sorted(values.unique().tolist())


def make_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()


with st.sidebar:
    st.header("Upload")
    uploaded = st.file_uploader("Upload original G-NetWiFi file", type=["txt", "csv", "xlsx", "xls"])
    st.markdown("This version always combines **connected WiFi + scanned WiFi**.")

if uploaded is None:
    st.info("Upload your original G-NetWiFi `.txt` file to begin.")
    st.stop()

raw = uploaded.getvalue()
df_raw = load_file(uploaded.name, raw)

connected = build_connected_table(df_raw)
scanned = build_scanned_table(df_raw)
all_data = pd.concat([connected, scanned], ignore_index=True, sort=False)

if all_data.empty:
    st.error("No usable WiFi records found. The file must contain SSID, BSSID, FREQ/Frequency, and RSSI columns.")
    st.stop()

preferred_order = [
    "Source", "Slot", "Timestamp", "SSID", "BSSID", "FREQ", "CHAN", "RSSI", "BANDWIDTH", "SECURITY", "PSK",
    "LinkSpeed", "Longitude", "Latitude", "Location", "Altitude", "Height", "Accuracy",
]
ordered_cols = [c for c in preferred_order if c in all_data.columns] + [c for c in all_data.columns if c not in preferred_order]
all_data = all_data[ordered_cols]
all_data["SSID"] = all_data["SSID"].astype(str).str.strip()
all_data["BSSID"] = all_data["BSSID"].astype(str).str.strip()
all_data["FREQ"] = pd.to_numeric(all_data["FREQ"], errors="coerce")
all_data["RSSI"] = pd.to_numeric(all_data["RSSI"], errors="coerce")

st.subheader("Combined data overview")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Original rows", f"{len(df_raw):,}")
m2.metric("Connected records", f"{len(connected):,}")
m3.metric("Scanned records", f"{len(scanned):,}")
m4.metric("Combined records", f"{len(all_data):,}")

st.subheader("Choose SSID, BSSID, and FREQ")

# Multi-select cascading filters. Leave any filter empty to include all values for that field.
c1, c2, c3, c4 = st.columns(4)
with c1:
    ssid_options = prepare_text_options(all_data["SSID"])
    selected_ssids = st.multiselect(
        "SSID - choose one or many",
        ssid_options,
        default=[],
        placeholder="Leave empty = All SSIDs",
    )

ssid_filtered = all_data.copy()
if selected_ssids:
    ssid_filtered = ssid_filtered[ssid_filtered["SSID"].isin(selected_ssids)]

with c2:
    bssid_options = prepare_text_options(ssid_filtered["BSSID"])
    selected_bssids = st.multiselect(
        "BSSID - choose one or many",
        bssid_options,
        default=[],
        placeholder="Leave empty = All BSSIDs",
    )

bssid_filtered = ssid_filtered.copy()
if selected_bssids:
    bssid_filtered = bssid_filtered[bssid_filtered["BSSID"].isin(selected_bssids)]

with c3:
    freq_values = sorted(bssid_filtered["FREQ"].dropna().astype(int).unique().tolist())
    freq_options = [str(v) for v in freq_values]
    selected_freqs = st.multiselect(
        "FREQ / Frequency (MHz) - choose one or many",
        freq_options,
        default=[],
        placeholder="Leave empty = All FREQ",
    )

filtered = bssid_filtered.copy()
if selected_freqs:
    selected_freqs_int = [int(v) for v in selected_freqs]
    filtered = filtered[filtered["FREQ"].isin(selected_freqs_int)]

with c4:
    source_options = prepare_text_options(filtered["Source"]) if "Source" in filtered.columns else []
    selected_sources = st.multiselect(
        "Source",
        source_options,
        default=[],
        placeholder="Leave empty = Connected + Scanned",
    )

if selected_sources:
    filtered = filtered[filtered["Source"].isin(selected_sources)]

st.caption(
    "Tip: you can select multiple APs at once. For example, choose SSID = UTHM, then select two BSSIDs "
    "such as a8:5b:f7:bc:3e:b2 and 48:b4:c3:5c:dd:31, then choose one or more FREQ values."
)

st.subheader("RSSI result")
r1, r2, r3, r4, r5 = st.columns(5)
r1.metric("Rows", f"{len(filtered):,}")
if not filtered.empty:
    r2.metric("Mean RSSI", f"{filtered['RSSI'].mean():.2f} dBm")
    r3.metric("Min RSSI", f"{filtered['RSSI'].min():.0f} dBm")
    r4.metric("Max RSSI", f"{filtered['RSSI'].max():.0f} dBm")
    r5.metric("Sources", ", ".join(filtered["Source"].dropna().unique().tolist()))
else:
    r2.metric("Mean RSSI", "-")
    r3.metric("Min RSSI", "-")
    r4.metric("Max RSSI", "-")
    r5.metric("Sources", "-")

# RSSI over time chart when Timestamp exists
if not filtered.empty and "Timestamp" in filtered.columns:
    chart_df = filtered[["Timestamp", "RSSI", "Source", "BSSID", "FREQ"]].copy()
    chart_df = chart_df.dropna(subset=["RSSI"])
    if not chart_df.empty:
        st.line_chart(chart_df.set_index("Timestamp")["RSSI"])

st.dataframe(filtered, use_container_width=True, height=450)

st.subheader("Summary by SSID / BSSID / FREQ")
if not filtered.empty:
    summary = (
        filtered.groupby(["SSID", "BSSID", "FREQ"], dropna=False)
        .agg(
            Count=("RSSI", "count"),
            Mean_RSSI=("RSSI", "mean"),
            Min_RSSI=("RSSI", "min"),
            Max_RSSI=("RSSI", "max"),
            Std_RSSI=("RSSI", "std"),
            Sources=("Source", lambda x: ", ".join(sorted(set(x.dropna().astype(str)))))
        )
        .reset_index()
        .sort_values(["SSID", "BSSID", "FREQ"])
    )
    st.dataframe(summary, use_container_width=True, height=240)
else:
    summary = pd.DataFrame()
    st.warning("No RSSI data matches your selected SSID/BSSID/FREQ.")

st.subheader("Download")
d1, d2, d3 = st.columns(3)
with d1:
    st.download_button(
        "Download filtered CSV",
        filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name="filtered_combined_gnetwifi_rssi.csv",
        mime="text/csv",
        disabled=filtered.empty,
    )
with d2:
    st.download_button(
        "Download filtered Excel",
        make_excel_bytes({"Filtered_RSSI": filtered}) if not filtered.empty else b"",
        file_name="filtered_combined_gnetwifi_rssi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=filtered.empty,
    )
with d3:
    st.download_button(
        "Download filtered + summary Excel",
        make_excel_bytes({"Filtered_RSSI": filtered, "Summary": summary}) if not filtered.empty else b"",
        file_name="combined_gnetwifi_rssi_with_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=filtered.empty,
    )

with st.expander("Show first 20 rows of combined data"):
    st.dataframe(all_data.head(20), use_container_width=True)

with st.expander("Show raw first 20 rows"):
    st.dataframe(df_raw.head(20), use_container_width=True)
