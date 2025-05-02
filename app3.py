# main python for functioning
# for running publically we use--> in cmd--> ngrok http 5000

# 33TCIL52XLV2ZSYKDKM3VC6RKY recovery code of plaid account- api 

from flask import Flask, render_template, request, redirect, session, send_file
from twilio.rest import Client
import random
import mysql.connector
from dotenv import load_dotenv
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io


load_dotenv()  # Load environment variables



account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

# Ensure Twilio phone number is valid
if not twilio_phone_number or not twilio_phone_number.startswith('+'):
    print("❌ Error: Invalid Twilio phone number format in .env file!")
    exit()

print(f" Twilio Phone Number Loaded: {twilio_phone_number}")


app = Flask(__name__)
app.secret_key = 'Pj123@'  # Change this for security


# Database connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Priyanka21@",
    database="finance_tracker"
)
cursor = conn.cursor()

# Twilio configuration

twilio_client = Client(account_sid, auth_token)

# Create tables if not exist
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    phone_number VARCHAR(15) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    date DATE NOT NULL,
    category VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)''')
conn.commit()

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            return redirect('/dashboard')
        else:
            print("Invalid credentials. Please try again.")
            return redirect('/register')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        phone_number = request.form['phone_number']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username=%s OR phone_number=%s", (username, phone_number))
        if cursor.fetchone():
            print("Username or phone number already exists! Try another one.")
            return redirect('/register')

        otp = random.randint(100000, 999999)
        session['otp'] = otp
        session['temp_user'] = {'username': username, 'phone_number': phone_number, 'password': password}

        try:
            twilio_client.messages.create(
                body=f"Your OTP is: {otp}",
                from_=twilio_phone_number,
                to=phone_number
            )
            print("OTP sent successfully! Please enter it below.",otp)
            return redirect('/verify')
        
        except Exception as e:
            print(f"Error sending OTP: {e}")
            return redirect('/register')
    
    return render_template('register.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if 'temp_user' not in session or 'otp' not in session:
        return redirect('/register')

    if request.method == 'POST':
        otp_code = request.form['otp_code']
        
        if str(session['otp']) == otp_code:
            user_data = session.pop('temp_user')
            session.pop('otp', None)
            cursor.execute("INSERT INTO users (username, phone_number, password) VALUES (%s, %s, %s)",
                           (user_data['username'], user_data['phone_number'], user_data['password']))
            conn.commit()
            print("Registration successful! Please log in.")
            return redirect('/login')
        
        print("Invalid OTP. Please try again.")
        return redirect('/verify')
    
    return render_template('verify_otp.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        cursor.execute("SELECT username FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        cursor.execute("SELECT * FROM expenses WHERE user_id=%s", (user_id,))
        expenses = cursor.fetchall()
        return render_template('dashboard.html', username=user[0], expenses=expenses)
    return redirect('/login')

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' in session:
        user_id = session['user_id']
        date = request.form['date']
        category = request.form['category']
        amount = request.form['amount']
        description = request.form['description']
        cursor.execute("INSERT INTO expenses (user_id, date, category, amount, description) VALUES (%s, %s, %s, %s, %s)",
                       (user_id, date, category, amount, description))
        conn.commit()
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/save_expenses')
def save_expenses():
    if 'user_id' in session:
        user_id = session['user_id']
        cursor.execute("SELECT date, category, amount, description FROM expenses WHERE user_id=%s", (user_id,))
        expenses = cursor.fetchall()
        df = pd.DataFrame(expenses, columns=['Date', 'Category', 'Amount', 'Description'])
        output = io.BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, mimetype="text/csv", as_attachment=True, download_name="expenses.csv")
    return redirect('/login')

@app.route('/upload_expenses', methods=['GET', 'POST'])
def upload_expenses():
    if 'user_id' in session:
        if request.method == 'POST':
            user_id = session['user_id']
            uploaded_file = request.files['file']

            if uploaded_file and uploaded_file.filename.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file)

                    # Insert data into database
                    for _, row in df.iterrows():
                        cursor.execute("""
                            INSERT INTO expenses (user_id, date, category, amount, description) 
                            VALUES (%s, %s, %s, %s, %s)
                        """, (user_id, row['Date'], row['Category'], row['Amount'], row['Description']))
                    
                    conn.commit()
                    return render_template('upload_expenses.html', message="File uploaded successfully!")
                
                except Exception as e:
                    return render_template('upload_expenses.html', message=f"Error processing file: {e}")

            return render_template('upload_expenses.html', message="Invalid file format! Please upload a CSV file.")

        return render_template('upload_expenses.html')

    return redirect('/login')

@app.route('/visualize')
def visualize_expenses():
    if 'user_id' in session:
        user_id = session['user_id']
        cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id=%s GROUP BY category", (user_id,))
        data = cursor.fetchall()
        if data:
            df = pd.DataFrame(data, columns=['Category', 'Amount'])
            plt.figure(figsize=(15, 6))
            sns.barplot(x='Category', y='Amount', data=df)
            plt.xticks(rotation=30)
            plt.title('Expenses by Category')
            plt.xlabel('Category')
            plt.ylabel('Total Amount')
            img = io.BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            return send_file(img, mimetype='image/png')
        else:
            return "No expenses to visualize!"
    return redirect('/login')



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')


# ##########################3 for bank linking
###########################################
# new 

from flask import jsonify, request, session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

openai_api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(api_key=openai_api_key, model="gpt-4o-mini")

@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({"reply": "Please log in first."})

    user_id = session['user_id']
    user_input = request.get_json().get('message', '').strip()

    if not user_input:
        return jsonify({"reply": "Please enter a valid message."})

    print("Logged in user ID:", user_id)
    print("User input:", user_input)

    # Define possible categories (can be dynamically fetched from the database)
    categories = ['Transport', 'Food', 'Entertainment', 'Utilities', 'Other']

    # Check if user input matches any of the predefined categories
    identified_category = None
    for category in categories:
        if category.lower() in user_input.lower():
            identified_category = category
            break

    # Expense-related queries
    if identified_category:
        try:
            conn.ping(reconnect=True)

            # Fetch all expenses by date for the category
           
            cursor.execute("""
                SELECT date AS expense_date, SUM(amount) AS daily_total
            FROM expenses
            WHERE user_id = %s AND category = %s
            GROUP BY date
            ORDER BY expense_date ASC
            """, (user_id, identified_category))

            rows = cursor.fetchall()

            if rows:
                 # Format the response
                expense_lines = [
                    f"On date- {row[0].strftime('%Y-%m-%d')} you spent- ₹{row[1]}"
                    for row in rows
                ]
                total = sum(row[1] for row in rows)
                
                response_text = "Here is your breakdown:<br><br>"
                response_text += "<br>".join(expense_lines)
                response_text += f"<br><br><strong>Total {identified_category} expenses:</strong> ₹{total}"

                
                return jsonify({"reply": response_text})
                
            else:
                return jsonify({
                    "reply": f"I couldn't find any {identified_category} expenses yet. Add some transactions to get started!"
                })
            
        except Exception as db_err:
            print("Database error:", db_err)
            return jsonify({"reply": "Error retrieving expense data."})


    # Handle general chatbot queries dynamically
    try:
        if "total" in user_input.lower() and "expense" in user_input.lower():
            cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=%s", (user_id,))
            total = cursor.fetchone()[0]
            if total:
                return jsonify({"reply": f"Your total expenses: ₹{total}"})
            else:
                return jsonify({"reply": "No expenses recorded yet."})
   
    # Compute total expense for context
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=%s", (user_id,))
        total = cursor.fetchone()[0] or 0

        system_message = f'''
        You are a smart assistant in a personal finance tracker app. 
        The user has spent a total of ₹{total} on various categories of expenses.
        Answer their query based on their inputs, focusing on expenses and financial data. 
        If the user has no data in the expenses table in the database, then respond that they should enter data first.
    '''

        # Pass the user input as a HumanMessage
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_input)
        ]
        
        # Invoke the assistant's response
        response = llm.invoke(messages)
        
        return jsonify({"reply": response.content})
    except Exception as e:
        print("LangChain error:", e)
        return jsonify({"reply": "Sorry, something went wrong. Try again later."})


if __name__ == '__main__':
    app.run(debug=True)
