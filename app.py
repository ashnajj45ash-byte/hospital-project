import os
from functools import wraps
from io import BytesIO
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash, send_file
)
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import database
from chatbot import rag_chatbot

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-this")

database.init_db()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access only.")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = database.verify_user(username, password)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user.get("role", "patient")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
    return render_template("login.html")


@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not username or not email or not password:
        flash("All fields are required to register.")
        return redirect(url_for("login"))

    success = database.create_user(username, email, password)
    if success:
        flash("Account created! Please log in.")
    else:
        flash("Username or email already exists.")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    history = database.get_chat_history(session["user_id"], limit=5)
    return render_template(
        "dashboard.html", username=session.get("username"), history=history
    )


@app.route("/history")
@login_required
def history_page():
    history = database.get_chat_history(session["user_id"], limit=50)
    return render_template(
        "history.html", username=session.get("username"), history=history
    )


@app.route("/chatbot")
@login_required
def chatbot_page():
    return render_template("chatbot.html", username=session.get("username"))


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()

    if not question:
        return jsonify({"error": "Message cannot be empty."}), 400

    try:
        result = rag_chatbot.ask(question)
    except Exception as exc:
        return jsonify({"error": f"Chatbot failed to respond: {exc}"}), 500

    database.log_chat(session["user_id"], question, result["answer"])

    return jsonify({"answer": result["answer"]})


@app.route("/api/order", methods=["POST"])
@login_required
def api_order():
    data = request.get_json(silent=True) or {}
    ordered_by = data.get("ordered_by", "patient")
    room_number = (data.get("room_number") or "").strip()
    items = data.get("items") or []
    notes = (data.get("notes") or "").strip()

    if not room_number:
        return jsonify({"error": "Room number is required."}), 400
    if not items:
        return jsonify({"error": "Select at least one item."}), 400

    items_str = ", ".join(items)
    database.log_food_order(session["user_id"], ordered_by, room_number, items_str, notes)

    return jsonify({"success": True, "message": "Order placed successfully."})


@app.route("/appointments", methods=["GET", "POST"])
@login_required
def appointments_page():
    if request.method == "POST":
        doctor_name = request.form.get("doctor_name", "").strip()
        department = request.form.get("department", "").strip()
        appointment_date = request.form.get("appointment_date", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip()

        if not all([doctor_name, department, appointment_date, appointment_time]):
            flash("Please fill in all appointment fields.")
        else:
            database.book_appointment(
                session["user_id"], doctor_name, department, appointment_date, appointment_time
            )
            flash("Appointment requested! We'll confirm it shortly.")
        return redirect(url_for("appointments_page"))

    appointments = database.get_user_appointments(session["user_id"])
    return render_template("appointments.html", username=session.get("username"), appointments=appointments)


@app.route("/appointments/cancel/<int:appointment_id>", methods=["POST"])
@login_required
def cancel_appointment_route(appointment_id):
    database.cancel_appointment(appointment_id, session["user_id"])
    flash("Appointment cancelled.")
    return redirect(url_for("appointments_page"))


@app.route("/medications", methods=["GET", "POST"])
@login_required
def medications_page():
    if request.method == "POST":
        medicine_name = request.form.get("medicine_name", "").strip()
        dosage = request.form.get("dosage", "").strip()
        timings = request.form.get("timings", "").strip()
        notes = request.form.get("notes", "").strip()

        if not medicine_name or not timings:
            flash("Medicine name and timings are required.")
        else:
            database.add_medication(session["user_id"], medicine_name, dosage, timings, notes)
            flash("Medication reminder added.")
        return redirect(url_for("medications_page"))

    medications = database.get_user_medications(session["user_id"])
    return render_template("medications.html", username=session.get("username"), medications=medications)


@app.route("/medications/delete/<int:medication_id>", methods=["POST"])
@login_required
def delete_medication_route(medication_id):
    database.delete_medication(medication_id, session["user_id"])
    flash("Medication reminder removed.")
    return redirect(url_for("medications_page"))


@app.route("/bills")
@login_required
def bills_page():
    bills = database.get_user_bills(session["user_id"])
    total_due = sum(b["amount"] for b in bills if b["status"] == "unpaid")
    return render_template(
        "bills.html", username=session.get("username"), bills=bills, total_due=total_due
    )


@app.route("/discharge-summary", methods=["GET", "POST"])
@login_required
def discharge_summary_page():
    if request.method == "POST":
        patient_name = request.form.get("patient_name", "").strip()
        diagnosis = request.form.get("diagnosis", "").strip()
        admission_date = request.form.get("admission_date", "").strip()
        discharge_date = request.form.get("discharge_date", "").strip()
        doctor_notes = request.form.get("doctor_notes", "").strip()

        if not patient_name or not admission_date or not discharge_date:
            flash("Patient name, admission date, and discharge date are required.")
            return redirect(url_for("discharge_summary_page"))

        summary_id = database.save_discharge_summary(
            session["user_id"], patient_name, diagnosis, admission_date, discharge_date, doctor_notes
        )
        return redirect(url_for("download_discharge_summary", summary_id=summary_id))

    return render_template("discharge_summary.html", username=session.get("username"))


@app.route("/discharge-summary/download/<int:summary_id>")
@login_required
def download_discharge_summary(summary_id):
    summary = database.get_discharge_summary(summary_id, session["user_id"])
    if not summary:
        flash("Discharge summary not found.")
        return redirect(url_for("discharge_summary_page"))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 60, "MediTrust AI - Discharge Summary")

    pdf.setFont("Helvetica", 11)
    y = height - 110
    lines = [
        f"Patient Name: {summary['patient_name']}",
        f"Admission Date: {summary['admission_date']}",
        f"Discharge Date: {summary['discharge_date']}",
        "",
        "Diagnosis:",
        summary['diagnosis'] or "N/A",
        "",
        "Doctor's Notes:",
        summary['doctor_notes'] or "N/A",
    ]
    for line in lines:
        for wrapped in [line[i:i+95] for i in range(0, max(len(line), 1), 95)]:
            pdf.drawString(50, y, wrapped)
            y -= 18
        if line == "":
            y -= 6

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(50, 40, f"Generated on {summary['created_at']} - MediTrust AI")

    pdf.save()
    buffer.seek(0)
    return send_file(
        buffer, as_attachment=True,
        download_name=f"discharge_summary_{summary_id}.pdf",
        mimetype="application/pdf",
    )


@app.route("/api/sos", methods=["POST"])
@login_required
def api_sos():
    data = request.get_json(silent=True) or {}
    room_number = (data.get("room_number") or "").strip()
    message = (data.get("message") or "").strip()

    if not room_number:
        return jsonify({"error": "Room number is required."}), 400

    database.log_sos(session["user_id"], room_number, message)
    return jsonify({"success": True, "message": "Emergency alert sent to staff."})


@app.route("/admin/add-bill", methods=["POST"])
@admin_required
def admin_add_bill():
    username = request.form.get("username", "").strip()
    description = request.form.get("description", "").strip()
    amount = request.form.get("amount", "").strip()

    user = None
    for u in database.get_all_users():
        if u["username"] == username:
            user = u
            break

    if not user:
        flash("No user found with that username.")
    elif not description or not amount:
        flash("Description and amount are required.")
    else:
        try:
            database.add_bill(user["id"], description, float(amount))
            flash(f"Bill added for {username}.")
        except ValueError:
            flash("Amount must be a number.")

    return redirect(url_for("admin_panel"))


@app.route("/admin/resolve-sos/<int:alert_id>", methods=["POST"])
@admin_required
def admin_resolve_sos(alert_id):
    database.resolve_sos(alert_id)
    flash("SOS alert marked as resolved.")
    return redirect(url_for("admin_panel"))


@app.route("/admin")
@admin_required
def admin_panel():
    users = database.get_all_users()
    chats = database.get_all_chat_history(limit=50)
    sos_alerts = database.get_active_sos_alerts()
    return render_template("admin.html", users=users, chats=chats, sos_alerts=sos_alerts)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
