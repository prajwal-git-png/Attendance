from flask import Flask, render_template, request, Response
import sqlite3
import os
from datetime import datetime
from datetime import timedelta
from pyzbar.pyzbar import decode 
import cv2
import qrcode

scanner_running = True
app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/attendance')
def view_attendance():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT * FROM attendance")
    attendance_data = c.fetchall()
    conn.close()
    return render_template('attendance.html', attendance_data=attendance_data)

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        student_name = request.form.get('student_name')
        if student_id and student_name:
            generate_qr(student_id, student_name) 
            mark_attendance(student_id, student_name)
            return "QR code generated successfully and attendance marked!"
        else:
            return "Please provide both student ID and name."
    else:
        return render_template('generate.html')

@app.route('/upload_qr', methods=['POST'])
def upload_qr():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'

        file = request.files['file']
        if not file:
            return 'No file selected'

        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            qr_data = decode_qr_code(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            if qr_data:
                qr_data_parts = qr_data.split(',')
                if len(qr_data_parts) >= 2:
                    student_id = qr_data_parts[0].strip()
                    student_name = ','.join(qr_data_parts[1:]).strip()
                    mark_attendance(student_id.strip(), student_name.strip())  
                    app.logger.info(f"Attendance marked for student ID: {student_id}, Name: {student_name}")
                    
                    return f"Attendance marked for student ID: {student_id}, Name: {student_name}"
                else:
                  
                   
                    student_id = qr_data.strip()  
                    mark_attendance(student_id.strip())
                    
                 
                    app.logger.info(f"Attendance marked for student ID: {student_id}")
                    
                    return f"Attendance marked for student ID: {student_id}"
            else:
                return "No QR code found in the uploaded image"

    return render_template('scan.html')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def generate_qr(student_id, student_name):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"{student_id},  \t  {student_name}") 
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img.save(f"qr_codes/{student_id}_{student_name}.png")

def decode_qr_code(image_path):
    image = cv2.imread(image_path)
    decoded_objects = decode(image)
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8')
    else:
        return None

def mark_attendance(student_id, student_name=None):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (student_id TEXT, student_name TEXT, date TEXT)''')
    
    if student_name:
        c.execute("SELECT * FROM attendance WHERE student_id = ? AND date >= datetime('now', '-1 day')", (student_id,))
    else:
        c.execute("SELECT * FROM attendance WHERE student_id = ? AND student_name IS NULL AND date >= datetime('now', '-1 day')", (student_id,))
    
    if c.fetchone():
        return "Attendance already marked for this student within the last 24 hours"
    
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if student_name:
        c.execute("INSERT INTO attendance (student_id, student_name, date) VALUES (?, ?, ?)", (student_id, student_name, date))
    else:
        c.execute("INSERT INTO attendance (student_id, date) VALUES (?, ?)", (student_id, date))
    
    conn.commit()
    conn.close()
    return "Attendance marked successfully"


@app.route('/video_feed')
def video_feed_route():
    return Response(video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_scanner')
def stop_scanner():
    global scanner_running
    if scanner_running:
        scanner_running = False
        return 'Scanner stopped'
    else:
        return 'Scanner is not running'


@app.route('/scanner_qr')

def scanner_qr():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    global scanner_running
    scanner_running = True
    cap = cv2.VideoCapture(0)
    
    while scanner_running:
        # Capture frame-by-frame
        ret, frame = cap.read()

        # Decode QR codes
        decoded_objects = decode(frame)
        
        # Check if QR code is detected
        if decoded_objects:
            for obj in decoded_objects:
                qr_data = obj.data.decode('utf-8')
                student_id, student_name = qr_data.split(',')  

                # Check if the student has already attended
                if (student_id):
                    feedback_message = 'Student already attended!'
                else:
                    # Mark attendance
                    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO attendance (student_id, student_name, date) VALUES (?, ?, ?)", (student_id, student_name, date))
                    conn.commit()
                    feedback_message = 'QR Code Detected - Attendance Marked'

                # Provide feedback
                cv2.putText(frame, feedback_message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Display the resulting frame
        cv2.imshow('QR Code Scanner', frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the camera and close all OpenCV windows
    cap.release()
    cv2.destroyAllWindows()

    # Fetch student attendance data from the database
    c.execute("SELECT * FROM attendance")
    attendance_data = c.fetchall()
    print(attendance_data)

    # Close the database connection
    conn.close()
    scanner_running = False
    return "Attendance scanning complete"
   
@app.route('/scan_qr')
def scan_qr():
    return render_template('scan.html')


if __name__ == '__main__':
    app.run(debug=True)
