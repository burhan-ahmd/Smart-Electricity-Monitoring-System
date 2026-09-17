import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta
import json
import asyncio

# # ==============================
# # SHEET AUTH
# # ==============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds)

SHEET_ID = "145a8Yr8T7QMUIAubVKb0k_WMfv7wd84svQoefbFXiZ8"


def get_clean_data():
    sheet = client.open_by_key(SHEET_ID).worksheet("Active Readings Data")

    raw_data = sheet.get_all_values()
    
    # print("RAW DATA:", raw_data)

    # ==============================
    # STEP 1: Extract headers
    # ==============================
    headers = raw_data[0]
    rows = raw_data[1:]

    clean_data = {}

    # ==============================
    # STEP 2: Process each row
    # ==============================
    for row in rows:
        row_dict = dict(zip(headers, row))

        date = row_dict["Date"]
        meter = row_dict["Meter"]

        # Convert numeric fields
        row_dict["Confidence"] = int(row_dict["Confidence"])
        row_dict["Last Reading"] = float(row_dict["Last Reading"])
        row_dict["Current Reading"] = float(row_dict["Current Reading"])
        row_dict["Usage"] = float(row_dict["Usage"])
        row_dict["Difference"] = float(row_dict["Difference"])

        # ==============================
        # STEP 3: Group by Date → Meter
        # ==============================
        if date not in clean_data:
            clean_data[date] = {}

        clean_data[date][meter] = row_dict

    return clean_data

# data = get_clean_data()
# print("Data: ", data)

# # ==============================
# # LOAD API FOR LLM
# # ==============================
load_dotenv()

# ==============================
# SETUP OF GOOGLE MODELS WITH THINKING LEVEL CONFIG
# ==============================

model_settings = GoogleModelSettings(google_thinking_config={'thinking_level': 'high'})  # 'low' or 'high'

primary_model = GoogleModel('gemini-3-flash-preview')
fallback_model = GoogleModel('gemini-3.1-flash-lite-preview')

agent_primary = Agent(
    primary_model, 
    system_prompt="You are an expert Data Analyst and Efficiency Consultant. Your task is to generate a premium-grade 'Utility Optimization Report' that is visually compelling, data-driven, and highly actionable for my clients.",          
    model_settings=model_settings
)

agent_fallback = Agent(
    fallback_model,
    system_prompt="You are an expert Data Analyst and Efficiency Consultant. Your task is to generate a premium-grade 'Utility Optimization Report' that is visually compelling, data-driven, and highly actionable for my clients.",          
    model_settings=model_settings
)


def build_precomputed_report_data(data):
    """
    Fully deterministic billing + forecasting engine

    Features:
    - Multi-interval smoothing (stable daily avg)
    - Per-meter forecasting
    - Group-level aggregation (Accounts for ON/OFF meters)
    - No LLM math dependency
    """

    # ==============================
    # SORT DATES
    # ==============================
    sorted_dates = sorted(
        data.keys(),
        key=lambda d: datetime.strptime(d, "%d/%m/%Y")
    )

    latest_date = sorted_dates[-1]
    prev_date = sorted_dates[-2] if len(sorted_dates) > 1 else None

    latest_day = data[latest_date]
    prev_day = data[prev_date] if prev_date else {}

    # ==============================
    # GROUP CONFIG (FUTURE SAFE)
    # ==============================
    groups = {
        "A": ["Meter 1", "Meter 2"],
        "B": ["Meter 3", "Meter 4"]
    }

    group_limits = {
        "A": 380,
        "B": 380
    }

    # ==============================
    # STEP 1: BUILD HISTORY (MULTI-INTERVAL)
    # ==============================
    meters_history = defaultdict(list)

    for i in range(1, len(sorted_dates)):
        prev_d = sorted_dates[i - 1]
        curr_d = sorted_dates[i]

        prev_day_data = data[prev_d]
        curr_day_data = data[curr_d]

        days = (
            datetime.strptime(curr_d, "%d/%m/%Y") -
            datetime.strptime(prev_d, "%d/%m/%Y")
        ).days or 1

        for meter in curr_day_data:
            if meter in prev_day_data:
                usage = (
                    curr_day_data[meter]["Current Reading"] -
                    prev_day_data[meter]["Current Reading"]
                )

                daily_avg = usage / days
                meters_history[meter].append(daily_avg)

    # ==============================
    # STEP 2: METERS FINAL CALCULATION
    # ==============================
    meters_result = {}
    billing_end = None
    remaining_days = 0

    for meter, info in latest_day.items():
        owner = info["Owner Name"]
        meter_no = info["Meter Number"]
        latest_usage = float(info["Usage"])
        
        # interval usage
        if prev_date and meter in prev_day:
            interval_usage = float(info["Current Reading"] - prev_day[meter]["Current Reading"])
        else:
            interval_usage = latest_usage

        # interval days
        if prev_date:
            d1 = datetime.strptime(prev_date, "%d/%m/%Y")
            d2 = datetime.strptime(latest_date, "%d/%m/%Y")
            interval_days = (d2 - d1).days or 1
        else:
            interval_days = 1

        # ------------------------------
        # Stable daily average (multi-interval smoothing)
        # ------------------------------
        history = meters_history.get(meter, [])
        if history:
            avg_daily = sum(history) / len(history)
        else:
            avg_daily = latest_usage  # fallback

        # ------------------------------
        # Billing cycle logic
        # ------------------------------
        billing_end = datetime.strptime(
            info["Last Reading Date"],
            "%d/%m/%Y"
        ) + timedelta(days=30)

        current_date = datetime.strptime(latest_date, "%d/%m/%Y")

        remaining_days = (billing_end - current_date).days
        remaining_days = max(0, remaining_days)

        # ------------------------------
        # FINAL PREDICTION (PER METER ONLY)
        # ------------------------------
        predicted_additional = avg_daily * remaining_days
        predicted_total = latest_usage + predicted_additional

        # --- NEW: 190 CROSS DATE LOGIC ---
        if avg_daily > 0:
            days_to_190 = (190 - latest_usage) / avg_daily
            if days_to_190 <= 0:
                cross_date_str = "Already Crossed"
            else:
                cross_date_val = current_date + timedelta(days=int(days_to_190))
                cross_date_str = f"{cross_date_val.day}, {cross_date_val.strftime('%B')}, {cross_date_val.year}"
        else:
            cross_date_str = "Will not cross"
        # ---------------------------------

        # assign group
        group = "A" if meter in groups["A"] else "B"

        meters_result[meter] = {
            "owner": owner,
            "meter_no": meter_no,
            "group": group,
            "total_usage": latest_usage,
            "interval_usage": round(interval_usage, 2),
            "interval_days": interval_days,
            "daily_avg": round(avg_daily, 2),
            "predicted_additional": round(predicted_additional, 2), # Used for Group math
            "predicted_usage": round(predicted_total, 2), 
            "expected_190_cross_date": cross_date_str,
            "history_points": len(history),
            "status": "ON"
        }

    # ==============================
    # STEP 3: GROUP CALCULATIONS (FIXED)
    # ==============================
    
    # 3a. Extract absolute latest usage for EVERY meter across the timeline
    # This ensures we catch inactive/OFF meters (like Meter 2 & 4) that aren't in 'latest_day'
    all_meters_latest_usage = {}
    for d in sorted_dates:
        for m_key, m_info in data[d].items():
            all_meters_latest_usage[m_key] = float(m_info["Usage"])

    # 3b. Aggregate usage by Groups
    groups_result = {}
    
    for g_name, meter_list in groups.items():
        g_limit = group_limits[g_name]
        
        # Sum the last known usage for all meters in this group
        total_group_usage = sum(all_meters_latest_usage.get(m, 0.0) for m in meter_list)
        
        # Calculate remaining capacity (allow negative if limit is breached)
        remaining_capacity = g_limit - total_group_usage
        
        # --- NEW PREDICTION LOGIC ---
        # Sum the predicted future usage of ONLY the active meters in this group
        group_predicted_additional = sum(
            meters_result[m]["predicted_additional"] for m in meter_list if m in meters_result
        )
        
        # Calculate the expected total usage at the very end of the billing month
        predicted_end_total = total_group_usage + group_predicted_additional
        # ----------------------------
        
        groups_result[f"Group {g_name}"] = {
            "Meters": ", ".join(meter_list),
            "Group Limit": f"{g_limit} units",
            "Total Group Usage": round(total_group_usage, 2),
            "Remaining Capacity": round(remaining_capacity, 2),
            "Predicted Additional (Next 10 Days)": round(group_predicted_additional, 2),
            "Predicted End-of-Month Total": round(predicted_end_total, 2)
        }
    
    # ==============================
    # STEP 4: META INFO
    # =============================
    
    # 1. Convert the string dates into datetime objects first
    report_date_obj = datetime.strptime(latest_date, "%d/%m/%Y")
    
    billing_start_str = latest_day[next(iter(latest_day))]["Last Reading Date"]
    billing_start_obj = datetime.strptime(billing_start_str, "%d/%m/%Y")

    # 2. Now it is safe to use .strftime()
    meta = {
        "report_date": report_date_obj.strftime("%d %b %Y"),
        "billing_start": billing_start_obj.strftime("%d %b"),
        "billing_end": billing_end.strftime("%d %b") if billing_end else None,
        "remaining_days": remaining_days
    }
    

    # ==============================
    # FINAL OUTPUT
    # ==============================
    return {
        "meta": meta,
        "meters": meters_result,
        "groups": groups_result
    }



def build_prompt(data):
    # Convert dict to string to pass to the LLM
    data_str = json.dumps(data, indent=2)

    return f"""Role: You are an expert Data Analyst and Efficiency Consultant. Your task is to generate a premium-grade "Smart Electricity Monitoring Report" that is visually compelling, data-driven, and highly actionable for my clients.

IMPORTANT RULES:
- All dates and numbers MUST come from the provided JSON data only.
- NEVER assume or hardcode any values.
- Formatting must be strictly for WhatsApp. Use single asterisks for bold (*Text*), NOT markdown (**Text**).
- Follow the structure, emojis, and exact spacing of the Expected Output Template.
- Replace "Muhammad" with "M." in owner names (e.g., "M. Ramzan").
- In Meter details, no need to mention dates.

────────────────────────────
⚙️ DATA MAPPING RULES (CRITICAL)

1. HEADER CALCULATION:
- Billing Period: Use `meta.billing_start` – `meta.billing_end`
- Report Date: Use `meta.report_date`

2. METERS BREAKDOWN (ON vs OFF):
- For ACTIVE meters (Meter 1, Meter 3) found in `meters` object: Map `total_usage`, `daily_avg`, `interval_usage`, `predicted_usage`, and `expected_190_cross_date`. Status is ON ✅.
- For INACTIVE meters (Meter 2, Meter 4) NOT in the `meters` object: You MUST deduce their usage. 
  * Meter 2 Total Usage = Group A `Total Group Usage` MINUS Meter 1 `total_usage`.
  * Meter 4 Total Usage = Group B `Total Group Usage` MINUS Meter 3 `total_usage`.
  * For these inactive meters, Daily Avg = 0, Last Interval = 0. No predictions or cross dates. Status is OFF ⛔.

3. GROUP ANALYSIS (PREDICTIONS):
- Use `groups.Total Group Usage` for Current Usage.
- Use `groups.Remaining Capacity` for Remaining Capacity.
- Map `groups.Predicted End-of-Month Total` directly to the "Expected Total" line.
- If Expected Total > Group Limit (380), mark with ❌ (Over limit). If under, mark with ✔️.

4. RECOMMENDATIONS:
- EXACTLY 3 short bullet points or use emojis for high alert!
- Use `groups.Predicted Additional` and `meta.remaining_days` to inform your advice (e.g., "Reduce usage by X units over the next 10 days").

────────────────────────────
📋 EXPECTED OUTPUT STYLE (STRICT TEMPLATE):
(Do not change this layout. Just fill in the dynamic data based on the JSON)

*Smart Electricity Monitoring Report*

📅 Billing Period: [meta.billing_start] – [meta.billing_end]
📍 Report Date: [meta.report_date]

━━━━━━━━━━━━━━━━━━━

📌 *Executive Summary*

🚨 Group A (Meter 1 & 2)
• Current Usage: [Total Group Usage] units
• Risk: HIGH (Will exceed limit)
• Action Needed: Immediate load reduction

✅ Group B (Meter 3 & 4)
• Current Usage: [Total Group Usage] units
• Status: Safe and stable

–  Limit Fixed (190 Units Each Meter)

━━━━━━━━━━━━━━━━━━━

📊 *Meter Details*

👤 M. Ramzan (Meter 1 – 632000)
• Total Usage: [total_usage] units
• Daily Avg: [daily_avg] units
• Last Interval Usage: [interval_usage] units
• Predicted Usage: [predicted_usage] units ⚠️
• Limit Reached On: [expected_190_cross_date]
• Status: ON ✅

👤 Imran Shabbir (Meter 2 – 633201)
• Total Usage: [Calculated] units
• Daily Avg: 0 units
• Last Interval Usage: 0 units
• Status: OFF ⛔

👤 Burhan Ahmed (Meter 3 – 633206)
• Total Usage: [total_usage] units
• Daily Avg: [daily_avg] units
• Last Interval Usage: [interval_usage] units
• Predicted Usage: [predicted_usage] units ✅
• Limit Reached On: [expected_190_cross_date]
• Status: ON ✅

👤 Irfan Shabbir (Meter 4 – 633204)
• Total Usage: [Calculated] units
• Daily Avg: 0 units
• Last Interval Usage: 0 units
• Status: OFF ⛔

━━━━━━━━━━━━━━━━━━━

📈 *Group Analysis*

⚠️ Group A Analysis (Meter 1 & Meter 2)
• Total Group Usage: [Total Group Usage] units
• Group Limit: 380 units
• Remaining Capacity: [Remaining Capacity] units
• Expected Total: [Predicted End-of-Month Total] units ❌ (Over limit)

✅ Group B Analysis (Meter 3 & Meter 4)
• Total Group Usage: [Total Group Usage] units
• Group Limit: 380 units
• Remaining Capacity: [Remaining Capacity] units
• Expected Total: [Predicted End-of-Month Total] units ✔️

━━━━━━━━━━━━━━━━━━━

💡 *Recommendations*

🔄 Shift load from Meter 1 immediately  
⛔ Keep Meter 2 & 4 OFF  
📉 Reduce Meter 1 usage to stay under limits

━━━━━━━━━━━━━━━━━━━

DATA TO PROCESS:
{data_str}
"""


async def data_analysis(prompt:str):
    print("🚀 Starting data analysis...")
    try:
        print("🧠 Using PRIMARY model...")
        response = await agent_primary.run([
            prompt, 
        ])
        print("✅ Primary Agent Worked successfully")
        
        return response.output
        
    except Exception as e:
        # 🔁 fallback model
        print("❌ Primary failed:", str(e))
        print("🔁 Switching to FALLBACK model...")
        
        response = await agent_fallback.run([
            prompt, 
        ])
        print("✅ Fallback Agent Worked successfully")
        return response.output


async def run_analysis():
    data = get_clean_data()   # ALWAYS fresh   
    # data = {'01/05/2026': {'Meter 2': {'Date': '01/05/2026', 'Active Meters': 'Meter 2, Meter 4', 'Meter': 'Meter 2', 'Owner Name': 'Imran Shabbir', 'Meter Number': '633201', 'Group With': 'Meter 1', 'Model': 'primary', 'Confidence': 100, 'Current Reading Date': '01/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 38386.0, 'Current Reading': 38567.0, 'Usage': 181.0, 'Difference': 181.15}, 'Meter 4': {'Date': '01/05/2026', 'Active Meters': 'Meter 2, Meter 4', 'Meter': 'Meter 4', 'Owner Name': 'Irfan Shabbir', 'Meter Number': '633204', 'Group With': 'Meter 3', 'Model': 'primary', 'Confidence': 100, 'Current Reading Date': '01/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 20125.0, 'Current Reading': 20276.0, 'Usage': 151.0, 'Difference': 151.28}, 'Meter 3': {'Date': '01/05/2026', 'Active Meters': 'Meter 3, Meter 1', 'Meter': 'Meter 3', 'Owner Name': 'Burhan Ahmed', 'Meter Number': '633206', 'Group With': 'Meter 4', 'Model': 'primary', 'Confidence': 95, 'Current Reading Date': '01/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 819.0, 'Current Reading': 841.0, 'Usage': 22.0, 'Difference': 22.5}, 'Meter 1': {'Date': '01/05/2026', 'Active Meters': 'Meter 3, Meter 1', 'Meter': 'Meter 1', 'Owner Name': 'Muhammad Ramzan', 'Meter Number': '632000', 'Group With': 'Meter 2', 'Model': 'fallback', 'Confidence': 95, 'Current Reading Date': '01/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 48205.0, 'Current Reading': 48239.0, 'Usage': 34.0, 'Difference': 34.37}}, '05/05/2026': {'Meter 4': {'Date': '05/05/2026', 'Active Meters': 'Meter 4, Meter 2', 'Meter': 'Meter 4', 'Owner Name': 'Irfan Shabbir', 'Meter Number': '633204', 'Group With': 'Meter 3', 'Model': 'primary', 'Confidence': 100, 'Current Reading Date': '05/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 20125.0, 'Current Reading': 20320.0, 'Usage': 195.0, 'Difference': 195.55}, 'Meter 2': {'Date': '05/05/2026', 'Active Meters': 'Meter 4, Meter 2', 'Meter': 'Meter 2', 'Owner Name': 'Imran Shabbir', 'Meter Number': '633201', 'Group With': 'Meter 1', 'Model': 'primary', 'Confidence': 99, 'Current Reading Date': '05/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 38386.0, 'Current Reading': 38573.0, 'Usage': 187.0, 'Difference': 187.86}, 'Meter 3': {'Date': '05/05/2026', 'Active Meters': 'Meter 3, Meter 1', 'Meter': 'Meter 3', 'Owner Name': 'Burhan Ahmed', 'Meter Number': '633206', 'Group With': 'Meter 4', 'Model': 'primary', 'Confidence': 100, 'Current Reading Date': '05/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 819.0, 'Current Reading': 845.0, 'Usage': 26.0, 'Difference': 26.3}, 'Meter 1': {'Date': '05/05/2026', 'Active Meters': 'Meter 3, Meter 1', 'Meter': 'Meter 1', 'Owner Name': 'Muhammad Ramzan', 'Meter Number': '632000', 'Group With': 'Meter 2', 'Model': 'primary', 'Confidence': 95, 'Current Reading Date': '05/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 48205.0, 'Current Reading': 48308.0, 'Usage': 103.0, 'Difference': 103.97}}, '06/05/2026': {'Meter 1': {'Date': '06/05/2026', 'Active Meters': 'Meter 1, Meter 3', 'Meter': 'Meter 1', 'Owner Name': 'Muhammad Ramzan', 'Meter Number': '632000', 'Group With': 'Meter 2', 'Model': 'primary', 'Confidence': 95, 'Current Reading Date': '06/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 48205.0, 'Current Reading': 48326.0, 'Usage': 121.0, 'Difference': 120.64}, 'Meter 3': {'Date': '06/05/2026', 'Active Meters': 'Meter 1, Meter 3', 'Meter': 'Meter 3', 'Owner Name': 'Burhan Ahmed', 'Meter Number': '633206', 'Group With': 'Meter 4', 'Model': 'primary', 'Confidence': 100, 'Current Reading Date': '06/05/2026', 'Last Reading Date': '16/04/2026', 'Last Reading': 819.0, 'Current Reading': 855.0, 'Usage': 36.0, 'Difference': 35.6}}}

    processed_data = build_precomputed_report_data(data)
    prompt = build_prompt(processed_data)
    return await data_analysis(prompt)


# analysis = asyncio.run(run_analysis())
# print(analysis)

# data = get_clean_data()
# processed = build_precomputed_report_data(data)
# print(processed)