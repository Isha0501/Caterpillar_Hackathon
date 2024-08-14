import streamlit as st
import pandas as pd
import plotly.express as px
import time

# Load datasets
df = pd.read_csv("ml_predictions.csv")
df2 = pd.read_csv("threshold_limits_clean.csv")

# Convert 'Time' column to datetime
df['Time'] = pd.to_datetime(df['Time'], utc=True)

# Streamlit configuration
st.set_page_config(
    page_title='Risk Monitoring Dashboard',
    page_icon='🚚',
    layout='wide'
)

# Sidebar for machine selection with buttons
st.sidebar.markdown("### Select a Machine")

# Machine selection (persistent)
if 'selected_machine' not in st.session_state:
    st.session_state.selected_machine = df['Machine'].iloc[0]  # Default to the first machine

# Display buttons for each machine
machines = list(pd.unique(df['Machine']))
for machine in machines:
    if st.sidebar.button(machine, key=machine):
        st.session_state.selected_machine = machine

# Display selected machine name
st.write(f"### Machine: {st.session_state.selected_machine}")

# Filter DataFrame based on the selected machine
filtered_df = df[df['Machine'] == st.session_state.selected_machine]

# Define the parameters
parameters = list(pd.unique(filtered_df['Parameter']))

# Placeholder for the graphs
placeholders = [st.empty() for _ in range(7)]  # 7 rows for 14 parameters

# Dictionary to keep track of alerts
alerts = {}

# Function to convert risk level to descriptive text and color
def get_risk_level_info(risk_level):
    if risk_level == 2:
        return "Low", "green"
    elif risk_level == 3:
        return "Medium", "orange"
    elif risk_level == 4:
        return "High", "red"
    else:
        return "Unknown", "gray"  # Fallback in case of unexpected values

# Function to update the graphs without refreshing the page
def update_graphs():
    now = pd.Timestamp.now(tz='UTC')  # Ensure timezone consistency
    one_minute_ago = now - pd.Timedelta(minutes=1)

    # Filter data for the last minute
    df_filtered = filtered_df[filtered_df['Time'] >= one_minute_ago]

    # Ensure data is sorted by time
    df_filtered = df_filtered.sort_values(by='Time')

    # Dictionary to keep track of new alerts
    new_alerts = {}

    # Update each graph in pairs (2 per row)
    for i in range(7):
        if i * 2 < len(parameters):
            param1 = parameters[i * 2]
            fig_col1, fig_col2 = placeholders[i].columns(2)

            # Plot for parameter 1
            with fig_col1:
                param1_df = df_filtered[df_filtered['Parameter'] == param1].tail(10)  # Limit to last 10 data points
                if not param1_df.empty:
                    try:
                        low_thresh = df2[df2['Parameter'] == param1]['Low Threshold'].values[0]
                        high_thresh = df2[df2['Parameter'] == param1]['High Threshold'].values[0]
                        risk_level = df2[df2['Parameter'] == param1]['Probability of Failure'].values[0]
                    except IndexError:
                        low_thresh = high_thresh = risk_level = None  # Handle missing values

                    fig1 = px.line(param1_df, x='Time', y='Value', title=f'{param1} Over Time', height=300)
                    fig1.update_xaxes(tickformat='%H:%M:%S', tickangle=45)

                    # Set y-axis range to ensure threshold lines are visible
                    y_min = low_thresh if pd.notna(low_thresh) else param1_df['Value'].min()
                    y_max = high_thresh if pd.notna(high_thresh) else param1_df['Value'].max()

                    # Add some padding to ensure visibility
                    y_min -= 0.05 * abs(y_min)
                    y_max += 0.05 * abs(y_max)

                    fig1.update_yaxes(range=[y_min, y_max])

                    if pd.notna(low_thresh):
                        fig1.add_hline(y=low_thresh, line_dash="dash", line_color="yellow", annotation_text="Low Threshold", annotation_position="top left")
                    if pd.notna(high_thresh):
                        fig1.add_hline(y=high_thresh, line_dash="dash", line_color="red", annotation_text="High Threshold", annotation_position="bottom left")

                    st.write(fig1)

                    # Alert handling
                    if risk_level is not None:
                        risk_level_text, color = get_risk_level_info(risk_level)
                        if pd.notna(low_thresh) and param1_df['Value'].min() < low_thresh:
                            new_alerts[param1] = f"<span style='color:{color}; font-weight:bold;'>{param1} has fallen below the Low Threshold! Risk Level: {risk_level_text}</span>"
                        elif pd.notna(high_thresh) and param1_df['Value'].max() > high_thresh:
                            new_alerts[param1] = f"<span style='color:{color}; font-weight:bold;'>{param1} has exceeded the High Threshold! Risk Level: {risk_level_text}</span>"

        # Check if there's a second parameter in this row
        if i * 2 + 1 < len(parameters):
            param2 = parameters[i * 2 + 1]

            # Plot for parameter 2
            with fig_col2:
                param2_df = df_filtered[df_filtered['Parameter'] == param2].tail(10)  # Limit to last 10 data points
                if not param2_df.empty:
                    try:
                        low_thresh = df2[df2['Parameter'] == param2]['Low Threshold'].values[0]
                        high_thresh = df2[df2['Parameter'] == param2]['High Threshold'].values[0]
                        risk_level = df2[df2['Parameter'] == param2]['Probability of Failure'].values[0]
                    except IndexError:
                        low_thresh = high_thresh = risk_level = None  # Handle missing values

                    fig2 = px.line(param2_df, x='Time', y='Value', title=f'{param2} Over Time', height=300)
                    fig2.update_xaxes(tickformat='%H:%M:%S', tickangle=45)

                    # Set y-axis range to ensure threshold lines are visible
                    y_min = low_thresh if pd.notna(low_thresh) else param2_df['Value'].min()
                    y_max = high_thresh if pd.notna(high_thresh) else param2_df['Value'].max()

                    # Add some padding to ensure visibility
                    y_min -= 0.05 * abs(y_min)
                    y_max += 0.05 * abs(y_max)

                    fig2.update_yaxes(range=[y_min, y_max])

                    if pd.notna(low_thresh):
                        fig2.add_hline(y=low_thresh, line_dash="dash", line_color="yellow", annotation_text="Low Threshold", annotation_position="top left")
                    if pd.notna(high_thresh):
                        fig2.add_hline(y=high_thresh, line_dash="dash", line_color="red", annotation_text="High Threshold", annotation_position="bottom left")

                    st.write(fig2)

                    # Alert handling
                    if risk_level is not None:
                        risk_level_text, color = get_risk_level_info(risk_level)
                        if pd.notna(low_thresh) and param2_df['Value'].min() < low_thresh:
                            new_alerts[param2] = f"<span style='color:{color}; font-weight:bold;'>{param2} has fallen below the Low Threshold! Risk Level: {risk_level_text}</span>"
                        elif pd.notna(high_thresh) and param2_df['Value'].max() > high_thresh:
                            new_alerts[param2] = f"<span style='color:{color}; font-weight:bold;'>{param2} has exceeded the High Threshold! Risk Level: {risk_level_text}</span>"

    # Display alerts in reverse order (newest first)
    for message in reversed(new_alerts.values()):
        st.sidebar.markdown(message, unsafe_allow_html=True)

# Initial graph update
update_graphs()

# Simulate real-time updates
while True:
    update_graphs()
    time.sleep(1)  # Update interval reduced to 10 seconds for better performance
