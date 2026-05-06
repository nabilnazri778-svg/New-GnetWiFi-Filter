# G-NetWiFi RSSI Filter App

This is a Streamlit web application for filtering G-NetWiFi Pro log data.

The app allows users to upload original `.txt` log files from G-NetWiFi Pro and filter RSSI readings based on:

- SSID
- BSSID
- Frequency / FREQ
- Source type: Connected WiFi or Scanned WiFi

## Features

- Supports original G-NetWiFi Pro `.txt` files
- Combines connected WiFi data and scanned WiFi data into one clean table
- Allows multiple SSID, BSSID, and FREQ selections
- Shows RSSI readings over time
- Provides summary statistics such as count, mean RSSI, minimum RSSI, and maximum RSSI
- Allows filtered data to be downloaded as CSV or Excel

## Files

This repository should contain:

```text
gnetwifi_multiselect_rssi_filter_app.py
requirements.txt
README.md
```

## How to Run Locally

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
streamlit run gnetwifi_multiselect_rssi_filter_app.py
```

## How to Use

1. Open the app.
2. Upload your original G-NetWiFi Pro `.txt` file.
3. Select one or more SSID values.
4. Select one or more BSSID values.
5. Select one or more frequency values.
6. View the filtered RSSI readings.
7. Download the filtered result if needed.

## Deployment

This app can be deployed using Streamlit Community Cloud.

When deploying, set the main file as:

```text
gnetwifi_multiselect_rssi_filter_app.py
```

## Privacy Note

Do not upload real WiFi log files containing sensitive location data to a public GitHub repository.

The app is designed so that users upload their `.txt` file inside the website when using the app.
