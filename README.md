# 🔒 LockIN: AI-Powered Remote Exam Proctoring System (Video Only)

## 🚀 Overview

**LockIN** is a real-time, AI-driven proctoring solution built on **Flask** and **SocketIO**. Its primary function is to monitor remote test-takers by analyzing their **video stream** for suspicious behavior, including unauthorized faces and objects. The system provides a centralized Admin Dashboard for full control over the exam environment and student intervention.

---

## 💻 Tech Stack

The system leverages asynchronous communication and powerful Computer Vision libraries:

* **Server/Backend:** Python, **Flask**, **Flask-SocketIO** (with **Eventlet**) for core application logic, state management, and high-performance real-time communication.
* **Video Analysis (ML):** **OpenCV** and **MediaPipe** (`face_mesh`) handle head pose estimation, gaze tracking, and multi-face/object detection logic.
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
| **People Swap** | Sudden, significant drop in the original student's face recognition match confidence. | **CRITICAL: 25 points** |
| **Phone Detection** | Object detection logic identifies a common mobile phone/device within the frame. | **CRITICAL: 25 points** |

### 2. Centralized Admin Dashboard Features

The Admin Dashboard provides full control over the exam environment and student intervention:

* **Exam Question Management:** Admins can set, upload, and push the exam questions to all connected student clients via a dedicated Flask route (`/set_questions`).
* **Student State Monitoring:** Real-time list of all students showing their current **Score** (starts at **100**), **Status**, and accumulated **Warnings**.
* **Alert Feed:** Instant, time-stamped log of all triggered violations.
* **Admin Power: Kickout** 🛑: Admins can manually send a **session_terminated** command via SocketIO to immediately disconnect any student from the exam session.

---

## 📂 Project Structure (Backend)

* `server.py`: The core application, handling SocketIO connections, global state management (`active_students`, `EXAM_QUESTIONS`), and coordination of analysis.
* `video_analysis.py`: Contains all the computer vision logic and violation detection rules.
* `requirements.txt`: Python dependencies needed to run the server and analysis.

---

## ▶️ Setup and Running

### 1. Installation

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### 2. Run the Server

Start the application:

```bash
python server.py
