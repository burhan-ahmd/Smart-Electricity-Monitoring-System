# from sheet import sheetdata
# # from main_ocr import process_two_meters
# # import asyncio


# user_data = sheetdata()
# # ocr_data = asyncio.run(process_two_meters("test_images/1.jpg", "test_images/3.jpg"))
# # print(ocr_data)

# ocr_data3 = {'Meter 1': {'digits': 841.5, 'confidence': 100, 'model': 'primary'}, 'Meter 2': {'digits': 20276.28, 'confidence': 100, 'model': 'fallback'}}
# ocr_data4 = {'Meter 1': {'digits': 20276.28, 'confidence': 100, 'model': 'fallback'}, 'Meter 2': {'digits': 841.5, 'confidence': 100, 'model': 'primary'}}


# # group 3,4 data

# ocr_data1 = {'Meter 1': {'digits': 38567.15, 'confidence': 100, 'model': 'primary'}, 'Meter 2': {'digits': 48239.37, 'confidence': 95, 'model': 'primary'}}
# ocr_data2 = {'Meter 1': {'digits': 48239.37, 'confidence': 95, 'model': 'primary'}, 'Meter 2': {'digits': 38567.15, 'confidence': 100, 'model': 'primary'}}

# # print(ocr_data)


# def fix_ocr_reading(ocr_value, last_value):
#     """
#     Fix decimal shift / missing digit OCR issues
#     """

#     # Already valid case
#     if ocr_value >= last_value:
#         return ocr_value

#     # Try scaling
#     candidates = [
#         ocr_value * 10,
#         ocr_value * 100,
#         ocr_value * 1000
#     ]

#     for val in candidates:
#         if val > last_value:
#             return val

#     return ocr_value  # fallback


def fix_ocr_reading(ocr_value, last_value, threshold=1000):
    """
    Fix decimal shift (both missing and extra decimals) / missing digit OCR issues
    """
    # 1. If it's already perfectly valid AND within normal range, keep it
    if last_value <= ocr_value <= (last_value + threshold):
        return ocr_value

    # 2. Try scaling both ways (divide for missing decimal, multiply for extra)
    candidates = [
        ocr_value / 1000,
        ocr_value / 100,
        ocr_value / 10,
        ocr_value * 10,
        ocr_value * 100,
        ocr_value * 1000
    ]

    best_val = ocr_value
    best_diff = float("inf")

    # 3. Find the candidate that makes the most logical sense
    for val in candidates:
        if val >= last_value:
            diff = val - last_value
            # It must be better than the previous best, AND under the threshold
            if diff < best_diff and diff <= threshold:
                best_diff = diff
                best_val = val

    return best_val  # Returns perfectly fixed decimal, or fallback if none work

def validate_and_map_meters(user_data, ocr_data, threshold=1000):
    """
    Validate OCR readings against ONLY active meters
    and map them correctly (even if order is wrong)
    """

    # 🔹 Step 1: Get active meters from sheet
    active = user_data["active_meters"]
    active_meters = [m.strip() for m in active.split(",") if m.strip()]

    # 🔹 Step 2: Prepare ONLY active meter data
    meters = {}
    meter_meta = {}

    for m in active_meters:
        key = m.lower().replace(" ", "")  # "Meter 1" → "meter1"

        last_reading = float(user_data[key]["last_month_reading"])

        meters[m] = last_reading

        # for smart error message
        meter_meta[m] = {
            "owner": user_data[key]["owner_name"],
            "number": user_data[key]["meter_number"]
        }

    # 🔹 Step 3: OCR readings (keep float here)
    ocr_values = []

    for key in ["Meter 1", "Meter 2"]:
        raw_value = float(ocr_data[key]["digits"])

        best_fixed = None
        best_diff = float("inf")

        for m in active_meters:
            meter_key = m.lower().replace(" ", "")
            last_val = float(user_data[meter_key]["last_month_reading"])

            # fixed = fix_ocr_reading(raw_value, last_val)
            fixed = fix_ocr_reading(raw_value, last_val, threshold)

            if fixed >= last_val:
                diff = fixed - last_val

                if diff < best_diff:
                    best_diff = diff
                    best_fixed = fixed

        # If nothing valid found → keep raw (will fail later safely)
        if best_fixed is None:
            best_fixed = raw_value

        print(f"OCR RAW: {raw_value} → FIXED: {best_fixed}")  # debug

        ocr_values.append((key, best_fixed, ocr_data[key]))

    mapping = {}
    used_meters = set()

    for ocr_name, ocr_value, full_data in ocr_values:
        best_meter = None
        best_diff = float("inf")

        for meter_name, last_value in meters.items():

            if meter_name in used_meters:
                continue

            # ❌ invalid: current < last month
            if ocr_value < last_value:
                continue

            diff = ocr_value - last_value

            if diff < best_diff:
                best_diff = diff
                best_meter = meter_name

        # ❌ No valid match → ERROR
        if best_meter is None or best_diff > threshold:

            active_info = "\n".join([
                f"- {m} (Owner: {meter_meta[m]['owner']}, No: {meter_meta[m]['number']})"
                for m in active_meters
            ])

            return {
                "status": "error",
                "message": f"""
You sent wrong meter image ({ocr_value}).

Active meters are:
{active_info}

Please send correct images.
"""
            }

        mapping[best_meter] = {
            "current": int(round(ocr_value)),  # ✅ convert to INT for usage
            "raw": ocr_value,          # keep float for debug
            "confidence": full_data["confidence"],
            "model": full_data["model"],
            "diff": best_diff          # float diff (useful insight)
        }

        used_meters.add(best_meter)

    return {
        "status": "success",
        "mapping": mapping
    } 


# results =  validate_and_map_meters(user_data, ocr_data2)

# print(results)

# if __name__ == "__main__":
#     user_data = {
#         "active_meters": "Meter 3, Meter 1",
#         "meter1": {
#             "owner_name": "Muhammad Ramzan",
#             "meter_number": "632000",
#             "last_month_reading": 48205
#         },
#         "meter3": {
#             "owner_name": "Burhan Ahmed",
#             "meter_number": "633206",
#             "last_month_reading": 819
#         }
#     }

#     # 🔥 YOUR PROBLEM CASE
#     ocr_test = {
#         "Meter 1": {"digits": 4832.564, "confidence": 95, "model": "primary"},
#         "Meter 2": {"digits": 854.6, "confidence": 100, "model": "primary"}
#     }

#     result = validate_and_map_meters(user_data, ocr_test)
#     print(result)