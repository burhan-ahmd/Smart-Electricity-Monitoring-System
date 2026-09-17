import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==============================
# AUTH
# ==============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds)

SHEET_ID = "145a8Yr8T7QMUIAubVKb0k_WMfv7wd84svQoefbFXiZ8"


# ==============================
# DATE FORMAT
# ==============================
def format_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%m/%d/%Y")
        return dt.strftime("%d/%m/%Y")
    except:
        return date_str


# ==============================
# CORE FUNCTION (IMPORTANT)
# ==============================
def sheetdata():
    sheet1 = client.open_by_key(SHEET_ID).worksheet("Form Responses 1")

    data = sheet1.get_all_values()

    if len(data) < 2:
        return None

    headers = data[0]
    latest = data[-1]

    def get(index):
        return latest[index].strip() if index < len(latest) else ""

    return {
        "name": get(2),
        "phone": get(3),
        "email": get(1),

        "meter1": {
            "owner_name": get(4),
            "meter_number": get(5),
            "last_month_reading": get(6),
            "last_reading_date": format_date(get(7)),
            "connected_with": get(8),
            "current_reading_date": format_date(get(9)),
            "current_reading": get(10),
        },

        "meter2": {
            "owner_name": get(11),
            "meter_number": get(12),
            "last_month_reading": get(13),
            "last_reading_date": format_date(get(14)),
            "connected_with": get(15),
            "current_reading_date": format_date(get(16)),
            "current_reading": get(17),
        },

        "meter3": {
            "owner_name": get(18),
            "meter_number": get(19),
            "last_month_reading": get(20),
            "last_reading_date": format_date(get(21)),
            "connected_with": get(22),
            "current_reading_date": format_date(get(23)),
            "current_reading": get(24),
        },

        "meter4": {
            "owner_name": get(25),
            "meter_number": get(26),
            "last_month_reading": get(27),
            "last_reading_date": format_date(get(28)),
            "connected_with": get(29),
            "current_reading_date": format_date(get(30)),
            "current_reading": get(31),
        },

        "active_meters": get(32),
        "converter_change_date": format_date(get(33)),
    }
    
    
# def update_latest_row(updates: dict):
#     """
#     updates example:
#     {
#         "meter1": 1234.5,
#         "meter3": 987.6
#     }
#     """

#     sheet1 = client.open_by_key(SHEET_ID).worksheet("Form Responses 1")
#     data = sheet1.get_all_values()

#     if len(data) < 2:
#         return False

#     row_number = len(data)

#     # 🔥 Map meters → column indexes (based on your sheet)
#     meter_column_map = {
#         "Meter 1": 11,
#         "Meter 2": 18,
#         "Meter 3": 25,
#         "Meter 4": 32
#     }

#     try:
#         for meter, value in updates.items():
#             if meter in meter_column_map:
#                 col = meter_column_map[meter]
#                 sheet1.update_cell(row_number, col, value)

#         print("Updated successfully")
#         return True

#     except Exception as e:
#         print("UPDATE ERROR:", str(e))
#         return False
    

def update_latest_row(updates: dict, full_data: dict):
    sheet1 = client.open_by_key(SHEET_ID).worksheet("Form Responses 1")
    processed_sheet = client.open_by_key(SHEET_ID).worksheet("Active Readings Data")

    data = sheet1.get_all_values()

    if len(data) < 2:
        return False

    row_number = len(data)

    meter_column_map = {
        "Meter 1": 11,
        "Meter 2": 18,
        "Meter 3": 25,
        "Meter 4": 32
    }

    try:
        # ==============================
        # 1. UPDATE ORIGINAL SHEET
        # ==============================
        for meter, value in updates.items():
            if meter in meter_column_map:
                col = meter_column_map[meter]
                sheet1.update_cell(row_number, col, value)

        # ==============================
        # 2. PREPARE DATA FOR NEW SHEET
        # ==============================
        date = full_data.get("Date", "")
        active_meters = ", ".join(full_data.get("active_meters", []))
        results = full_data.get("results", {})

        # 👉 Extract day from date (dd/mm/yyyy)
        try:
            day = int(date.split("/")[0])
        except:
            day = 1  # fallback

        # 🎨 COLOR LOGIC (your requirement)
        if day % 2 == 0:
            # Even date → Light Blue (slightly darker)
            color = {
                "red": 0.75,
                "green": 0.85,
                "blue": 1.0
            }
        else:
            # Odd date → Light Gray
            color = {
                "red": 0.9,
                "green": 0.9,
                "blue": 0.9
            }

        # ==============================
        # 3. GET START ROW BEFORE INSERT
        # ==============================
        start_row = len(processed_sheet.get_all_values()) + 1

        rows_to_add = []

        for meter_name, meter_data in results.items():
            row = [
                date,
                active_meters,
                meter_name,
                meter_data.get("Owner Name", ""),
                meter_data.get("Meter Number", ""),
                meter_data.get("Group With", ""),
                meter_data.get("Model", ""),
                meter_data.get("Confidence", ""),
                meter_data.get("Current Reading Date", ""),
                meter_data.get("Last Readers Reading Date", ""),
                meter_data.get("Last Readers Reading", ""),
                meter_data.get("Current Reading", ""),
                meter_data.get("Usage", ""),
                meter_data.get("Difference_from_last", "")
            ]
            rows_to_add.append(row)

        # ==============================
        # 4. APPEND ROWS (FAST)
        # ==============================
        processed_sheet.append_rows(rows_to_add)

        # ==============================
        # 5. APPLY COLOR TO THESE ROWS
        # ==============================
        num_rows = len(rows_to_add)

        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": processed_sheet.id,
                        "startRowIndex": start_row - 1,
                        "endRowIndex": start_row - 1 + num_rows
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ]

        processed_sheet.spreadsheet.batch_update({
            "requests": requests
        })

        print("✅ Updated + Logged + Colored successfully")
        return True

    except Exception as e:
        print("UPDATE ERROR:", str(e))
        return False


# userdata = sheetdata()

# meter_current1 = "48239"
# meter_current3 = "841"
# update = update_latest_row(meter_current1, meter_current3)

# print(update,userdata)