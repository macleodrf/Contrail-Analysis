# contrail_persistence.py
# Analyzes contrail persistence at 200–300 hPa using Wyoming radiosonde data
# Run in Grok or Python, fill prompts interactively. See User Guide on X: [Link to guide].

import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime, timedelta

print("""
GROK ANALYSIS of CONTRAIL PERSISTENCE
=====================================
Enter data to analyze contrail persistence (200–300 hPa):
- Times in 'HHZ DD Mon YYYY' (e.g., '12Z 12 Apr 2025') or 'YYYY-MM-DD HH:MM' (e.g., '2025-04-12 12:00').
- Observation time must be 00Z or 12Z.
- Paste radiosonde data from Wyoming (300–200 hPa, PRES, TEMP, DWPT).
See User Guide on X for details: [Link to guide or post].
""")

def saturation_vapor_pressure_ice(T_c):
    return 6.112 * np.exp((22.46 * T_c) / (T_c + 272.62))

def saturation_vapor_pressure_water(Td_c):
    return 6.112 * np.exp((17.67 * Td_c) / (Td_c + 243.5))

def calculate_rhi(T_c, Td_c):
    e = saturation_vapor_pressure_water(Td_c)
    e_si = saturation_vapor_pressure_ice(T_c)
    return (e / e_si) * 100

def contrail_persistence(rhi):
    return "Persistent contrails possible" if rhi >= 100 else "Persistent contrails not possible"

def suggest_closest_obs_time(img_dt):
    img_hour = img_dt.hour
    img_date = img_dt.date()
    if img_hour < 6:
        return datetime(img_date.year, img_date.month, img_date.day, 0), "00Z"
    elif img_hour < 18:
        return datetime(img_date.year, img_date.month, img_date.day, 12), "12Z"
    else:
        next_day = img_date + timedelta(days=1)
        return datetime(next_day.year, next_day.month, next_day.day, 0), "00Z"

def parse_time_input(time_str, allow_any_time=False, suggested_time=None):
    try:
        dt = datetime.strptime(time_str, "%HZ %d %b %Y")
    except ValueError:
        try:
            dt = datetime.strptime(time_str, "%Y-%-m-%d %H:%M")
        except ValueError:
            print("Error: Use 'HHZ DD Mon YYYY' (e.g., '12Z 12 Apr 2025') or 'YYYY-MM-DD HH:MM' (e.g., '2025-04-12 12:00').")
            if suggested_time:
                print(f"Suggested observation time: {suggested_time}")
            return None, time_str
    if not allow_any_time:
        obs_hour = dt.hour
        obs_minute = dt.minute
        if not ((obs_hour == 0 or obs_hour == 12) and obs_minute <= 15):
            print("Error: Observation time must be at 00Z or 12Z (e.g., '00Z 12 Apr 2025' or '2025-04-12 00:00').")
            if suggested_time:
                print(f"Suggested observation time: {suggested_time}")
            return None, time_str
    return dt, time_str

def check_time_proximity(obs_dt, img_dt, suggested_time):
    time_diff = abs(obs_dt - img_dt)
    if time_diff > timedelta(hours=6):
        return False, f"Observation time is more than 6 hours from image time. Suggested observation time: {suggested_time}"
    return True, ""

# Interactive input prompts
nws_id_station = input("NWS ID and Station Name (e.g., '72365 - ABQ Albuquerque'): ")
while not nws_id_station.strip():
    print("Error: Station name cannot be empty.")
    nws_id_station = input("NWS ID and Station Name (e.g., '72365 - ABQ Albuquerque'): ")

image_time_date = input("Image Date and Time UTC (e.g., '01Z 12 Apr 2025' or '2025-04-12 01:00'): ")
img_dt, image_time_date = parse_time_input(image_time_date, allow_any_time=True)
while img_dt is None:
    image_time_date = input("Image Date and Time UTC (e.g., '01Z 12 Apr 2025' or '2025-04-12 01:00'): ")
    img_dt, image_time_date = parse_time_input(image_time_date, allow_any_time=True)

suggested_dt, suggested_z = suggest_closest_obs_time(img_dt)
suggested_time = suggested_dt.strftime("%HZ %d %b %Y")
obs_time_date = input(f"Observation Time and Date UTC (e.g., '00Z 12 Apr 2025' or '2025-04-12 00:00', suggested: {suggested_time}): ")
obs_dt, obs_time_date = parse_time_input(obs_time_date, allow_any_time=False, suggested_time=suggested_time)
while obs_dt is None:
    obs_time_date = input(f"Observation Time and Date UTC (e.g., '00Z 12 Apr 2025' or '2025-04-12 00:00', suggested: {suggested_time}): ")
    obs_dt, obs_time_date = parse_time_input(obs_time_date, allow_any_time=False, suggested_time=suggested_time)

is_valid_time, time_error = check_time_proximity(obs_dt, img_dt, suggested_time)
if not is_valid_time:
    print(f"Warning: {time_error}")
    print("Proceeding with calculations, but results may be less accurate.")

image_location = input("Image Location - nearest town or region (e.g., 'Albuquerque, NM' or 'Central New Mexico'): ")
while not image_location.strip():
    print("Error: Location cannot be empty.")
    image_location = input("Image Location - nearest town or region (e.g., 'Albuquerque, NM' or 'Central New Mexico'): ")

print("\nRadiosonde Data (paste from Wyoming archive, 300–200 hPa, press Enter twice to finish):")
lines = []
while True:
    line = input()
    if line == "":
        if not lines:
            print("Error: Radiosonde data cannot be empty.")
            continue
        break
    lines.append(line)
user_data = "\n".join(lines)

# Data processing
try:
    df = pd.read_csv(StringIO(user_data), delim_whitespace=True)
    df = df.rename(columns={'PRES': 'P', 'TEMP': 'T', 'DWPT': 'Td'})
    if not all(col in df.columns for col in ['P', 'T', 'Td']):
        raise ValueError("Data must include PRES, TEMP, and DWPT columns.")
    if not df['P'].between(200, 300).any():
        raise ValueError("Data must include at least one level between 200 and 300 hPa.")
except Exception as e:
    print(f"Error: {e}. Please check your input format.")
    exit()

df['RHi'] = df.apply(lambda row: calculate_rhi(row['T'], row['Td']), axis=1)
df_flight = df[df['P'].between(200, 300)].copy()
levels = [200.0, 250.0, 300.0]
rhi_results = {}
for level in levels:
    if level in df_flight['P'].values:
        rhi = df_flight.loc[df_flight['P'] == level, 'RHi'].iloc[0]
        rhi_results[level] = rhi
    else:
        rhi_results[level] = None
if not df_flight.empty:
    max_rhi_row = df_flight.loc[df_flight['RHi'].idxmax()]
    max_rhi = max_rhi_row['RHi']
    max_rhi_level = max_rhi_row['P']
    max_rhi_t = max_rhi_row['T']
    max_rhi_td = max_rhi_row['Td']
else:
    max_rhi = None
    max_rhi_level = None

# Output results
print("\nCONTRAIL PERSISTENCE ANALYSIS")
print("============================")
print(f"NWS ID and Station: {nws_id_station}")
print(f"Observation Time: {obs_time_date} UTC")
print(f"Image Time: {image_time_date} UTC")
print(f"Image Location: {image_location}")
print("\nRHi at Flight Levels (200–300 hPa):")
for level in levels:
    rhi = rhi_results[level]
    if rhi is not None:
        persistence = contrail_persistence(rhi)
        print(f"{level} hPa: RHi = {rhi:.2f}%, {persistence}")
    else:
        print(f"{level} hPa: Not found in data")
if max_rhi is not None:
    max_persistence = contrail_persistence(max_rhi)
    print(f"\nMaximum RHi: {max_rhi:.2f}% at {max_rhi_level} hPa")
    print(f"T = {max_rhi_t:.1f}°C, Td = {max_rhi_td:.1f}°C")
    print(f"{max_persistence}")
else:
    print("\nNo data available in 200–300 hPa range.")
 
