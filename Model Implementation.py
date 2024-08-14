import numpy as np
import pandas as pd
import os
import time
import re
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from twilio.rest import Client

# Twilio credentials
account_sid = '...'  # Replace with your Twilio Account SID
auth_token = '...'  # Replace with your Twilio Auth Token
twilio_number = '...'  # Replace with your Twilio Phone Number
recipient_number = '+91...'  # Replace with the recipient's phone number

# Load the threshold limits once
threshold_limits = pd.read_csv('Threshold.csv')


# Function to extract low and high thresholds
def extract_thresholds(threshold_str):
    low_threshold = None
    high_threshold = None

    if 'Low' in threshold_str:
        low_part = threshold_str.split('Low')[1].split(',')[0].strip()
        low_threshold_match = re.match(r'[\d.]+', low_part)
        if low_threshold_match:
            low_threshold = low_threshold_match.group(0)

    if 'High' in threshold_str:
        high_part = threshold_str.split('High')[1].strip()
        high_threshold_match = re.match(r'[\d.]+', high_part)
        if high_threshold_match:
            high_threshold = high_threshold_match.group(0)

    return low_threshold, high_threshold


threshold_limits[['Low Threshold', 'High Threshold']] = threshold_limits['Treshold'].apply(
    lambda x: pd.Series(extract_thresholds(x)))
threshold_limits_clean = threshold_limits.drop(columns=['Treshold'])
encoding_map = {'Low': 2, 'Medium': 3, 'High': 4}
threshold_limits_clean['Probability of Failure'] = threshold_limits_clean['Probability of Failure'].map(encoding_map)

threshold_limits_clean.to_csv('threshold_limits_clean.csv',
                              index=False)


# Define the risk calculation function
def calculate_risk(row):
    value = row['Value']
    try:
        low_threshold = float(row['Low Threshold']) if pd.notna(row['Low Threshold']) else float('inf')
    except ValueError:
        low_threshold = float('inf')

    try:
        high_threshold = float(row['High Threshold']) if pd.notna(row['High Threshold']) else float('-inf')
    except ValueError:
        high_threshold = float('-inf')

    probability_of_failure = row['Probability of Failure']

    if value < low_threshold or value > high_threshold:
        return probability_of_failure
    else:
        return 1


# Function to send SMS
def send_sms(message):
    client = Client(account_sid, auth_token)
    client.messages.create(
        body=message,
        from_=twilio_number,
        to=recipient_number
    )
    print(f"SMS sent to {recipient_number}")


# Function to process the data, make predictions, and check conditions
def process_data_and_predict():
    dataset = pd.read_csv('synthetic_machine_data.csv')

    def create_new_parameter(df):
        if df['Component'] == 'Misc' or df['Component'] == 'Drive':
            return df['Parameter']
        else:
            return f"{df['Component']} {df['Parameter']}"

    dataset['New_Parameter'] = dataset.apply(create_new_parameter, axis=1)

    def replace_parameter(param):
        if param == 'Fuel Water in Fuel':
            return 'Water Fuel'
        elif param == 'Air Filter Pressure':
            return 'Air Filter Pressure Drop'
        else:
            return param

    dataset['New_Parameter'] = dataset['New_Parameter'].apply(replace_parameter)

    df_train, df_test = train_test_split(dataset, test_size=0.3, random_state=42)

    df_train = df_train.drop(columns=['Component', 'Parameter'])
    merged_df = pd.merge(df_train, threshold_limits_clean, left_on='New_Parameter', right_on='Parameter', how='left')
    merged_df['Risk'] = merged_df.apply(calculate_risk, axis=1)
    result_df = merged_df.drop(columns=['Parameter', 'Probability of Failure', 'Low Threshold', 'High Threshold'])
    df_train = result_df

    # Model training
    X_train = df_train.drop(columns=['Risk'])
    y_train = df_train['Risk'].fillna(0)

    X_test = df_test.copy()

    # Ensure the Time column is in datetime format
    X_train['Time'] = pd.to_datetime(X_train['Time'])
    X_test['Time'] = pd.to_datetime(X_test['Time'])

    # Keep the original time column for sorting later
    X_train = pd.get_dummies(X_train, columns=['Machine', 'New_Parameter'])
    X_test = pd.get_dummies(X_test, columns=['Machine', 'New_Parameter'])

    X_train, X_test = X_train.align(X_test, join='left', axis=1, fill_value=0)

    model = XGBClassifier()
    model.fit(X_train.drop(columns=['Time']), y_train)

    predictions = model.predict(X_test.drop(columns=['Time']))
    df_test['Risk'] = predictions

    # Sort the test DataFrame by the original 'Time' column to ensure sequential order
    df_test = df_test.sort_values(by='Time')

    # Calculate counts of risks
    count_4 = (df_test['Risk'] == 4).sum()
    count_3 = (df_test['Risk'] == 3).sum()
    count_2 = (df_test['Risk'] == 2).sum()

    # Check the conditions and send an SMS if met
    if count_2 >= 200:
        send_sms("Attention - Low-Level Alert!-  https://www.youtube.com/watch?v=QNzaDCCyTGE")
    if count_3 >= 350:
        send_sms("Attention - Medium-Level Alert! Please contact us for assistance at 000-800-100-1647.")
    if count_4 > 150:
        send_sms(
            "Attention - Medium-Level Alert! Schedule an appointment with Caterpillar team https://www.cat.com/en_IN/support/contact-us.html")

    # Update the output file
    df_test.to_csv('ml_predictions.csv', index=False)
    print("Updated predictions written to ml_predictions.csv")


# Main loop to run the process continuously
while True:
    process_data_and_predict()
    print("Waiting for new data...")
    time.sleep(1)  # Adjust the delay as needed