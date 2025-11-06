import csv
import random
from datetime import date, timedelta

# --- Configuration ---
# You can easily change these parameters to generate different data.

OUTPUT_FILENAME = 'generated_mess_data.csv'
DAYS_TO_GENERATE = 30
BASE_ATTENDANCE = 180  # The average number of students on a normal day.

# --- Dish Definitions ---
# Define the menu items. The script will randomly pick from these lists.
VEG_DISHES = [
    "Paneer Butter Masala", "Dal Tadka", "Veg Korma", "Chole Bhature",
    "Aloo Gobi", "Rajma Chawal", "Poha", "Idli Sambhar"
]
NON_VEG_DISHES = [
    "Chicken Curry", "Egg Curry", "Fish Fry", "Chicken Biryani"
]
SPECIAL_DISHES = [
    "Special Veg Thali", "Special Chicken Thali", "Gulab Jamun Special", "Paneer Tikka"
]

# --- Attendance Modifiers ---
# These values will be multiplied by the base attendance to simulate real-world variations.
MODIFIERS = {
    "day_of_week": {
        0: 1.0,   # Monday
        1: 1.05,  # Tuesday
        2: 1.1,   # Wednesday (often higher)
        3: 1.0,   # Thursday
        4: 0.9,   # Friday (might be lower)
        5: 0.8,   # Saturday (lower as students may go home)
        6: 0.95,  # Sunday (might be higher for special meals)
    },
    "dish_type": {
        "veg": 1.0,
        "nonveg": 1.15, # Non-veg dishes might attract more students
    },
    "is_special": 1.25, # Special dishes have a significant impact
    "meal_time": {
        "Lunch": 0.95, # Lunch might have slightly lower attendance than dinner
        "Dinner": 1.05,
    }
}

# --- Holiday Definitions ---
# Define holidays within your desired date range. Format: "YYYY-MM-DD": "Holiday Name"
# Example for the past month (from mid-September to mid-October 2025):
HOLIDAYS = {
    "2025-10-02": "Gandhi Jayanti",
    "2025-09-25": "Local Festival", # Example of a local holiday
}


def generate_data():
    """
    Generates synthetic mess attendance data for the last 30 days and saves it to a CSV file.
    """
    header = ['date', 'day_of_week', 'dish', 'dish_type', 'is_special', 'holiday', 'attended_students', 'meal_time']
    
    # Using a list to store data rows before writing to the file
    data_rows = []
    
    start_date = date.today() - timedelta(days=DAYS_TO_GENERATE)
    
    # Loop through each day in the specified period
    for i in range(DAYS_TO_GENERATE):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        day_of_week_str = current_date.strftime("%a") # e.g., "Mon"
        day_of_week_index = current_date.weekday() # 0 for Monday, 6 for Sunday
        
        # Loop through both meal times for each day
        for meal_time in ["Lunch", "Dinner"]:
            
            # --- Initialize default values for the meal ---
            attended_students = BASE_ATTENDANCE
            holiday_name = HOLIDAYS.get(date_str, 'None')
            
            # --- Handle Holidays ---
            if holiday_name != 'None':
                attended_students = random.randint(20, 50) # Significantly lower attendance on holidays
                dish = "Holiday Special"
                dish_type = "veg"
                is_special = True
            
            # --- Handle Regular Days ---
            else:
                # Decide which dish to serve
                # Let's make non-veg more likely on Wed, Fri, Sun
                if day_of_week_index in [2, 4, 6] and random.random() < 0.6:
                    dish = random.choice(NON_VEG_DISHES + SPECIAL_DISHES)
                else:
                    dish = random.choice(VEG_DISHES + SPECIAL_DISHES)
                    
                # Determine dish properties
                is_special = dish in SPECIAL_DISHES
                dish_type = "nonveg" if dish in NON_VEG_DISHES else "veg"
                
                # --- Calculate Attendance ---
                # 1. Apply day of week modifier
                attended_students *= MODIFIERS["day_of_week"][day_of_week_index]
                # 2. Apply dish type modifier
                attended_students *= MODIFIERS["dish_type"][dish_type]
                # 3. Apply meal time modifier
                attended_students *= MODIFIERS["meal_time"][meal_time]
                # 4. Apply special dish modifier
                if is_special:
                    attended_students *= MODIFIERS["is_special"]
                
                # 5. Add some random noise to make it look more real
                attended_students += random.randint(-15, 15)

            # --- Final Assembly of the Row ---
            row = {
                'date': date_str,
                'day_of_week': day_of_week_str,
                'dish': dish,
                'dish_type': dish_type,
                'is_special': is_special,
                'holiday': holiday_name,
                'attended_students': max(0, int(attended_students)), # Ensure attendance is not negative
                'meal_time': meal_time,
            }
            data_rows.append(row)

    # --- Write data to CSV file ---
    try:
        with open(OUTPUT_FILENAME, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(data_rows)
        print(f"Successfully generated {len(data_rows)} records.")
        print(f"Data saved to '{OUTPUT_FILENAME}'")
    except IOError:
        print(f"Error: Could not write to the file '{OUTPUT_FILENAME}'.")


if __name__ == '__main__':
    generate_data()
