import os
import requests
from datetime import datetime, timezone, date, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

BOOK_URL = "https://burntends.com.sg/reservations/"
API_URL = "https://www.restaurants.sg/apiv4/services.php/booking/getdaysrulesbooking/"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://www.restaurants.sg",
    "Referer": "https://www.restaurants.sg/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

TIMESLOTS_LUNCH = ["12:00", "12:15", "12:30", "12:45", "13:00"]
TIMESLOTS_DINNER = ["18:00", "18:15", "18:30", "18:45", "19:00", "19:15", "19:30"]

def get_target_dates():
    # All dates from today onwards for the rest of 2026
    target_months = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    dates = []
    for month in target_months:
        start = date(2026, month, 1)
        end = date(2027, 1, 1) if month == 12 else date(2026, month + 1, 1)
        current = start
        while current < end:
            if current > date.today():
                dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
    return dates

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def check_availability(mealtype, timeslots):
    target_dates = get_target_dates()
    payload = {
        "restaurant": "SG_SG_R_BurntEnds",
        "dates": target_dates,
        "mealtype": mealtype,
        "product": "RestaurantMainDining",
        "timeslots": timeslots,
        "token": "098oi12"
    }
    response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
    data = response.json()
    raw_slots = data.get("data", [])

    # Filter to only available slots (first field = "1")
    # NOTE: Same 70% confidence caveat as Ovenbird
    available = [s for s in raw_slots if s.split("|")[0] == "1"]
    return available

def parse_slots(raw_slots):
    # Group available slots by date
    by_date = {}
    for slot in raw_slots:
        parts = slot.split("|")
        if len(parts) >= 6:
            party_size = parts[2]
            slot_date = parts[5]
            if slot_date not in by_date:
                by_date[slot_date] = set()
            by_date[slot_date].add(f"party of {party_size}")
    return by_date

def main():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Missing Telegram credentials.")
        exit(1)

    now = datetime.now(timezone.utc).strftime('%H:%M UTC')
    print(f"Burnt Ends bot running at {now}")

    send_telegram(f"Burnt Ends bot is running!\nChecking all dates for rest of 2026.")

    found_any = False

    for mealtype, timeslots in [("lunch", TIMESLOTS_LUNCH), ("dinner", TIMESLOTS_DINNER)]:
        try:
            print(f"  Checking {mealtype}...")
            raw_slots = check_availability(mealtype, timeslots)

            if raw_slots:
                by_date = parse_slots(raw_slots)
                for slot_date, sizes in sorted(by_date.items()):
                    send_telegram(
                        f"BURNT ENDS - SLOTS OPEN!\n"
                        f"Date: {slot_date}\n"
                        f"Meal: {mealtype.capitalize()}\n"
                        f"Available for: {', '.join(sorted(sizes))}\n"
                        f"Book NOW: {BOOK_URL}"
                    )
                    print(f"  Alert sent for {slot_date} {mealtype}!")
                    found_any = True

        except Exception as e:
            print(f"  Error checking {mealtype}: {e}")

    if not found_any:
        print("No available slots found.")

if __name__ == "__main__":
    main()
