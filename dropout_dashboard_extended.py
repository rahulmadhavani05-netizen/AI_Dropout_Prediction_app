import streamlit as st
import pandas as pd
import numpy as np
import smtplib
from email.mime.text import MIMEText

# Constants
NUM_STUDENTS = 1000
STANDARDS = [str(i) for i in range(1, 13)]
DIVISIONS = ['A', 'B', 'C', 'D']

# Generate synthetic student data (fallback)
def generate_student_data(num_students):
    np.random.seed(42)
    student_ids = [f"S{str(i).zfill(4)}" for i in range(1, num_students+1)]
    names = [f"Student_{i}" for i in range(1, num_students+1)]
    standards = np.random.choice(STANDARDS, num_students)
    divisions = np.random.choice(DIVISIONS, num_students)
    
    attendance = np.random.uniform(50, 100, num_students).round(2)
    attempts = np.random.randint(1, 6, num_students)  # attempts per subject
    test_scores = np.random.uniform(30, 100, (num_students, 3)).round(2)
    fee_delay_days = np.random.choice([0, 0, 0, 10, 20, 30], num_students)
    
    data = pd.DataFrame({
        'StudentID': student_ids,
        'Name': names,
        'Standard': standards,
        'Division': divisions,
        'Attendance%': attendance,
        'Attempts': attempts,
        'Test1_Score': test_scores[:,0],
        'Test2_Score': test_scores[:,1],
        'Test3_Score': test_scores[:,2],
        'Fee_Delay_Days': fee_delay_days
    })
    return data

# Risk calculation function
def calculate_risk(row):
    risk_score = 0
    if row['Attendance%'] < 75:
        risk_score += 2
    if row['Attempts'] > 3:
        risk_score += 2
    if row['Test3_Score'] < row['Test2_Score'] < row['Test1_Score']:
        risk_score += 1
    if row['Fee_Delay_Days'] > 15:
        risk_score += 1
    
    if risk_score >= 4:
        return 'High'
    elif risk_score >= 2:
        return 'Medium'
    else:
        return 'Low'

# Color coding for risk levels
def risk_color(risk):
    if risk == 'High':
        return 'red'
    elif risk == 'Medium':
        return 'orange'
    else:
        return 'green'

# Email sending function
def send_email(to_email, subject, body, smtp_server, smtp_port, sender_email, sender_password):
    msg = MIMEText(body.strip())  # remove leading/trailing newlines
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email
    
    smtp_port = int(smtp_port)  # ensure port is integer
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())

# Main app
def main():
    st.title("AI-based Drop-out Prediction and Counseling Dashboard")
    
    st.sidebar.header("Upload Data Files (Optional)")
    attendance_file = st.sidebar.file_uploader("Upload Attendance CSV", type=['csv'])
    test_scores_file = st.sidebar.file_uploader("Upload Test Scores CSV", type=['csv'])
    fee_payment_file = st.sidebar.file_uploader("Upload Fee Payment CSV", type=['csv'])
    
    if attendance_file and test_scores_file and fee_payment_file:
        try:
            attendance_df = pd.read_csv(attendance_file)
            test_scores_df = pd.read_csv(test_scores_file)
            fee_payment_df = pd.read_csv(fee_payment_file)
            
            # Merge on 'StudentID'
            data = attendance_df.merge(test_scores_df, on='StudentID', how='outer')
            data = data.merge(fee_payment_df, on='StudentID', how='outer')
            
            # Fill missing values
            data.fillna({
                'Attendance%': 0,
                'Attempts': 1,
                'Fee_Delay_Days': 0,
                'Standard': 'Unknown',
                'Division': 'Unknown',
                'Name': 'Unknown',
                'Test1_Score': 0,
                'Test2_Score': 0,
                'Test3_Score': 0
            }, inplace=True)
            
            st.success("Data files uploaded and merged successfully.")
        except Exception as e:
            st.error(f"Error processing uploaded files: {e}")
            st.info("Using synthetic data instead.")
            data = generate_student_data(NUM_STUDENTS)
    else:
        st.info("Upload all three data files or use synthetic data.")
        data = generate_student_data(NUM_STUDENTS)
    
    # Calculate risk
    data['Risk_Level'] = data.apply(calculate_risk, axis=1)
    
    # Filters
    st.sidebar.header("Filter Students")
    standards_available = sorted(data['Standard'].unique())
    divisions_available = sorted(data['Division'].unique())
    risk_levels = ['Low', 'Medium', 'High']
    
    selected_standard = st.sidebar.multiselect("Select Standard(s)", options=standards_available, default=standards_available)
    selected_division = st.sidebar.multiselect("Select Division(s)", options=divisions_available, default=divisions_available)
    selected_risk = st.sidebar.multiselect("Select Risk Level(s)", options=risk_levels, default=risk_levels)
    
    filtered_data = data[
        (data['Standard'].isin(selected_standard)) &
        (data['Division'].isin(selected_division)) &
        (data['Risk_Level'].isin(selected_risk))
    ]
    
    st.write(f"### Showing {len(filtered_data)} students")
    
    # Display data with color-coded risk
    def color_risk(val):
        color = risk_color(val)
        return f'background-color: {color}; color: white; font-weight: bold'
    
    display_cols = ['StudentID', 'Name', 'Standard', 'Division', 'Attendance%', 'Attempts',
                    'Test1_Score', 'Test2_Score', 'Test3_Score', 'Fee_Delay_Days', 'Risk_Level']
    display_df = filtered_data[display_cols]
    st.dataframe(display_df.style.applymap(color_risk, subset=['Risk_Level']))
    
    # Risk distribution chart
    st.write("### Risk Level Distribution")
    risk_counts = filtered_data['Risk_Level'].value_counts().reindex(risk_levels).fillna(0)
    st.bar_chart(risk_counts)
    
    # Email configuration inputs
    st.sidebar.header("Email Configuration for Notifications")
    smtp_server = st.sidebar.text_input("SMTP Server", value="smtp.gmail.com")
    smtp_port = st.sidebar.number_input("SMTP Port", value=465)
    sender_email = st.sidebar.text_input("Sender Email")
    sender_password = st.sidebar.text_input("Sender Email Password", type="password")
    mentor_email = st.sidebar.text_input("Mentor Email")
    
    # Send email notifications button
    if st.button("Send Email Notifications to Mentors for High Risk Students"):
        if not all([smtp_server, smtp_port, sender_email, sender_password, mentor_email]):
            st.error("Please fill all email configuration fields.")
        else:
            high_risk_students = filtered_data[filtered_data['Risk_Level'] == 'High']
            if high_risk_students.empty:
                st.info("No high-risk students to notify.")
            else:
                sent_count = 0
                for _, row in high_risk_students.iterrows():
                    subject = f"Alert: High Risk Student {row['Name']} ({row['StudentID']})"
                    body = f"""
Student Details:
Name: {row['Name']}
ID: {row['StudentID']}
Standard: {row['Standard']}
Division: {row['Division']}
Attendance: {row['Attendance%']}%
Attempts: {row['Attempts']}
Latest Test Scores: {row['Test1_Score']}, {row['Test2_Score']}, {row['Test3_Score']}
Fee Delay Days: {row['Fee_Delay_Days']}
Risk Level: {row['Risk_Level']}

Please take timely counseling action.
""".strip()
                    try:
                        send_email(mentor_email, subject, body, smtp_server, smtp_port, sender_email, sender_password)
                        st.write(f"Email sent for {row['Name']} (ID: {row['StudentID']})")
                        sent_count += 1
                    except Exception as e:
                        st.error(f"Failed to send email for {row['Name']}: {e}")
                st.success(f"Emails sent for {sent_count} students.")

if __name__ == "__main__":
    main()
