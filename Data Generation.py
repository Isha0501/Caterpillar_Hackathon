import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# Define machine types and components
machines = ['Excavator', 'Articulated_Truck', 'Backhoe_Loader', 'Dozer', 'Crawler_Loader']
components = {
    'Engine': ['Engine Oil Pressure', 'Engine Temperature', 'Engine Speed'],
    'Fuel': ['Water Fuel', 'Fuel Temperature', 'Fuel Level', 'Fuel Pressure'],
    'Drive': ['Brake Control', 'Pedal Sensor', 'Transmission Pressure'],
    'Misc': ['Air Filter Pressure Drop', 'System Voltage', 'Exhaust Gas Temperature', 'Hydraulic Pump Rate']
}

# Threshold values for parameters
thresholds = {
    'Engine Oil Pressure': {'low': 25, 'high': 65, 'probability': 'High'},
    'Engine Temperature': {'high': 105, 'probability': 'High'},
    'Engine Speed': {'high': 1800, 'probability': 'Medium'},
    'Brake Control': {'low': 1, 'probability': 'Medium'},
    'Transmission Pressure': {'low': 200, 'high': 450, 'probability': 'Medium'},
    'Pedal Sensor': {'high': 4.7, 'probability': 'Low'},
    'Water Fuel': {'high': 1800, 'probability': 'High'},
    'Fuel Level': {'low': 1, 'probability': 'Low'},
    'Fuel Pressure': {'low': 35, 'high': 65, 'probability': 'Low'},
    'Fuel Temperature': {'high': 400, 'probability': 'High'},
    'System Voltage': {'low': 12.0, 'high': 15.0, 'probability': 'High'},
    'Exhaust Gas Temperature': {'high': 365, 'probability': 'High'},
    'Hydraulic Pump Rate': {'high': 125, 'probability': 'Medium'},
    'Air Filter Pressure Drop': {'low': 20, 'probability': 'Medium'},
}

# Initial values for each parameter (to start from a realistic scenario)
initial_values = {
    'Engine Oil Pressure': 50,
    'Engine Temperature': 90,
    'Engine Speed': 1200,
    'Brake Control': 2,
    'Transmission Pressure': 300,
    'Pedal Sensor': 3.5,
    'Water Fuel': 10,
    'Fuel Level': 50,
    'Fuel Pressure': 50,
    'Fuel Temperature': 100,
    'System Voltage': 13.5,
    'Exhaust Gas Temperature': 200,
    'Hydraulic Pump Rate': 100,
    'Air Filter Pressure Drop': 25,
}

# Rate of change for parameters per second
rate_of_change = {
    'Engine Oil Pressure': 0.1,
    'Engine Temperature': 0.5,
    'Engine Speed': 10,
    'Brake Control': 0.05,
    'Transmission Pressure': 2,
    'Pedal Sensor': 0.02,
    'Water Fuel': 5,
    'Fuel Level': -0.1,  # Fuel level typically decreases
    'Fuel Pressure': 0.1,
    'Fuel Temperature': 0.5,
    'System Voltage': 0.01,
    'Exhaust Gas Temperature': 1,
    'Hydraulic Pump Rate': 1,
    'Air Filter Pressure Drop': 0.1,
}

# Function to generate data for each parameter
def generate_value(parameter, value, rate, thresholds, intentional=False):
    if intentional:
        if parameter in thresholds:
            if 'high' in thresholds[parameter] and value < thresholds[parameter]['high']:
                value = thresholds[parameter]['high'] + np.random.uniform(0.1, 10)  # Cross threshold
            elif 'low' in thresholds[parameter] and value > thresholds[parameter]['low']:
                value = thresholds[parameter]['low'] - np.random.uniform(0.1, 10)  # Cross threshold
    else:
        if parameter in thresholds:
            if 'low' in thresholds[parameter] and value <= thresholds[parameter]['low']:
                value += abs(rate) * np.random.rand()
            elif 'high' in thresholds[parameter] and value >= thresholds[parameter]['high']:
                value -= abs(rate) * np.random.rand()
            else:
                value += rate * (np.random.rand() - 0.5)  # Random walk
        else:
            value += rate * (np.random.rand() - 0.5)  # Random walk
    return max(value, 0)  # Ensure no negative values

# Continuous real-time data generation
start_time = datetime.utcnow()
data = []
id_counter = 1

# Define the file path
file_path = 'synthetic_machine_data.csv'

# Initialize CSV file with headers
df = pd.DataFrame(columns=['Id', 'Time', 'Machine', 'Component', 'Parameter', 'Value'])
df.to_csv(file_path, index=False)

try:
    while True:
        current_time = datetime.utcnow()
        for machine in machines:
            for component, params in components.items():
                for param in params:
                    # Determine if this iteration should cross a threshold
                    intentional_failure = (int((current_time - start_time).total_seconds()) % 15 == 0)
                    current_value = initial_values[param]
                    roc = rate_of_change[param]
                    new_value = generate_value(param, current_value, roc, thresholds, intentional_failure)
                    initial_values[param] = new_value
                    data.append({
                        'Id': id_counter,
                        'Time': current_time.isoformat() + 'Z',
                        'Machine': machine + '_1',  # Append _1 to the machine name for uniqueness
                        'Component': component,
                        'Parameter': param,
                        'Value': round(new_value, 2)
                    })
                    id_counter += 1

        # Convert to DataFrame and append to CSV
        df = pd.DataFrame(data)
        df.to_csv(file_path, mode='a', header=False, index=False)
        data.clear()  # Clear the data list for the next round
        time.sleep(1)  # Sleep for 1 second to simulate real-time data generation

except KeyboardInterrupt:
    print("\nData generation stopped by user.")