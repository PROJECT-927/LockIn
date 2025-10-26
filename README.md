# 🔒 LockIN: AI-Powered Remote Exam Proctoring System

## 🚀 Overview

**LockIN** is a real-time, AI-driven proctoring solution built on **Flask** and **SocketIO**. Its primary function is to monitor remote test-takers by analyzing their **video stream** for suspicious behavior, including unauthorized faces and objects. The system provides a centralized Admin Dashboard for full control over the exam lifecycle and student intervention.

----

## 💻 Tech Stack

The system leverages asynchronous communication and powerful Computer Vision libraries:

* **Server/Backend:** Python, **Flask**, **Flask-SocketIO** (with **Eventlet**) for core application logic, state management, and high-performance real-time communication.  
* **Video Analysis (ML):** **OpenCV**, **MediaPipe** (`face_mesh`), and **DeepFace** for advanced facial analysis. DeepFace utilizes an embedded face recognition model, typically stored as a **.h5 file**, for identity verification and detecting **People Swap**.  
* **Utilities:** `numpy`, `python-dotenv`, and `base64` for data handling and configuration.

---

## ⚙️ Key Features and Logic

### 1. Real-Time Video Analysis & Critical Violations
The system actively monitors for the following infractions, triggering an immediate and significant score penalty:

| Violation Event | Detection Logic | Penalty (Example) |
| :--- | :--- | :--- |
| **No Face Detected** | Student leaves the camera frame. | **15 points** |
| **Looking Away** | Head pose tracking shows distraction for > **3.0 seconds**. | **5 points** |
| **Distracted Gaze** | Eye movement indicates looking significantly away from the screen. | **2 points** |
| **Multiple Faces** | More than one distinct face detected in the frame. | **CRITICAL: 25 points** |
| **People Swap** | Uses **DeepFace** identity verification to detect a sudden change in the student's face relative to the registered reference image. | **CRITICAL: 25 points** |
| **Phone Detection** | Object detection logic identifies a common mobile phone/device within the frame. | **CRITICAL: 25 points** |

---

### 2. Centralized Admin Dashboard Features

The Admin Dashboard provides full control over the exam environment and student intervention:

* **Exam Question Management:** Admins can set, upload, and push the exam questions to all connected student clients via a dedicated Flask route (`/set_questions`).  
* **Student State Monitoring:** Real-time list of all students showing their current **Score** (starts at **100**), **Status**, and accumulated **Warnings**.  
* **Alert Feed:** Instant, time-stamped log of all triggered violations.  
* **Admin Power: Kickout** 🛑: Admins can manually send a **session_terminated** command via SocketIO to immediately disconnect any student from the exam session.

---

## 📂 Project Structure (Backend)

* `server.py`: The core application, handling SocketIO connections, global state management (`active_students`, `EXAM_QUESTIONS`), and coordination of analysis.  
* `video_analysis.py`: Contains all the computer vision logic, DeepFace integration, and violation detection rules.  
* `requirements.txt`: Python dependencies needed to run the server and analysis.

---

## ▶️ Setup and Running

### 1. Installation

1. Navigate to the backend directory:
    ```bash
    cd backend
    ```
2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

---

### 2. Run the Backend Server

Start the application:

```bash
python server.py
```

The server will be running on **http://0.0.0.0:8000**, ready to accept SocketIO connections.

---

### 3. Running the Frontend (Client Side) 🔑

The frontend client applications (**Student Exam Interface** and **Admin Dashboard**) are expected to be available as separate HTML/JS files (`exam.html` and `admin.html`).

#### A. Student Client (e.g., `exam.html`)

Access the student interface by opening the file directly in a modern web browser.

**Login Credentials:**
```
Student ID: student@test.com
Password: password
```

**Connection:**  
The client establishes a SocketIO connection to `http://localhost:8000` and immediately starts streaming video frames.

---

#### B. Admin Dashboard (e.g., `admin.html`)

Access the admin interface by opening the file directly in a modern web browser.

**Login Credentials:**
```
Admin ID: admin@lockin.com
Password: password
```

**Connection:**  
The admin client connects to `http://localhost:8000` to receive real-time updates and execute control actions (**Kickout**, **Set Questions**).
