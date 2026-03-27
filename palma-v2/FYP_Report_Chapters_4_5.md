
# CHAPTER FOUR: PROJECT DEVELOPMENT, IMPLEMENTATION AND EVALUATION

## 4.1 Introduction
This chapter covers the implementation and integration of the PalmaCount system, detailing the interactions between the frontend interface, the backend logic, and the database management system. It outlines the tools, frameworks, and methodologies utilized to ensure a seamless transition from design to valid deployment. Furthermore, this chapter highlights the evaluation of the system through rigorous testing phases to ensure robustness and user satisfaction.

## 4.2 System Integration
The integration of the frontend, backend, and database in PalmaCount is designed to ensure a smooth workflow, real-time image analysis, and a seamless user experience. The system employs a microservices-like architecture where the user-facing web application communicates with a specialized deep learning inference service.

### Frontend and Backend Integration
**Technology Stack:**
*   **Frontend:** Flask (Python web framework) serving HTML5 templates, styled with Cascading Style Sheets (CSS) and Tailwind CSS for a modern, responsive user interface.
*   **Backend Interface:** A dedicated FastAPI service that hosts the deep learning model.
*   **Deep Learning Model:** YOLOv8 (You Only Look Once version 8) for object detection and tree counting.

**How Integration Works:**
The integration relies on RESTful API communication. When a user uploads an image via the Flask frontend:
1.  The Flask application receives the image and validates the file.
2.  It sends an HTTP `POST` request to the FastAPI backend service (`/predict` endpoint), passing the image data.
3.  The FastAPI backend runs the image through the YOLOv8 model (`inference.py`).
4.  The model returns detection results (coordinates, confidence scores, and classes) along with calculated analytics (tree counts, area estimation).
5.  FastAPI packages these results into a JSON response, including Base64-encoded visualizations (annotated images and charts), and sends it back to the Flask frontend for display.

### Backend and Database Integration
**Database:**
*   **System:** PostgreSQL (Production) / SQLite (Development) via SQLAlchemy ORM.
*   **Note:** While initial designs may have considered Firebase, the final implementation utilizes a relational database structure for robust relationship management between Users and Analyses.

**How Integration Works:**
The Flask backend acts as the intermedium between the application logic and the database:
1.  **ORM Mapping:** SQLAlchemy maps Python classes (e.g., `User`, `Analysis`) directly to database tables.
2.  **Data Persistence:** When an analysis is completed, the Flask app creates a new `Analysis` record containing the tree counts, calculated area (in square meters and hectares), and file paths.
3.  **Querying:** For the user dashboard and history features, the backend utilizes SQL queries to retrieve specific datasets linked to the logged-in user's ID, ensuring data isolation and security.

### Frontend and Database Direct Integration (Authentication & Data)
**Authentication:**
*   **Mechanism:** Server-side session management using Flask-Login concepts.
*   **Process:**
    *   **Registration:** Users submit credentials via the registration form. The backend hashes the password using secure algorithms (`werkzeug.security`) before storing it in the `users` table.
    *   **Login:** The system verifies the hashed password. Upon success, a session token (`user_id`) is stored in the user's browser cookie.
    *   **Access Control:** The frontend uses this session token to restrict access to secure pages (e.g., Dashboard, Upload, History).

**Recent Image Analysis:**
The frontend retrieves analysis history directly through the backend's routing logic:
1.  When a user visits the "History" or "Dashboard" page, the server queries the database for all records matching the current `session['user_id']`.
2.  The data is injected into the HTML templates (`history.html`) during server-side rendering, allowing the user to view their past uploads, tree counts, and yield estimates instantly.

## 4.3 System Output
**Final Output Display:**
The system presents the analysis results in a comprehensive dashboard view (`analysis_detail.html`):
1.  **Annotated Image:** The original drone imagery overlaid with bounding boxes distinguishing between "Mature" (Healthy/Yellow/Dead) and "Young" palms.
2.  **Statistical Summary:** A clear breakdown of total counts for each category.
3.  **Area Estimation:** Calculated plantation area in hectares and square meters based on canopy coverage.
4.  **Visual Analytics:** Generated charts (donut charts for composition, histograms for crown size) to provide actionable insights.

*(Figure 4.1: Example of System Output showing detected trees and statistics)*
> [Place Final Output Image Here]

## 4.4 System Testing
System testing focuses on verifying individual functions, classes, and workflows to ensure they meet technical and business requirements.

### 4.4.1 User Acceptance Testing (UAT)
UAT ensures the application meets user expectations and is ready for real-world deployment.

**End User Participation:**
*   Conducted sessions with plantation managers and estate owners.
*   Users were asked to perform core tasks:
    1.  Register a new account.
    2.  Log in to the system.
    3.  Upload a drone image for processing.
    4.  Review the analysis results and charts.

**Feedback Collection:**
Users provided feedback on User Interface (UI), User Experience (UX), performance, and feature usability.
*   **Positive:** "Everything is easy to navigate and works finely.", "The breakdown of data in charts is very helpful."
*   **Constructive:** "Confused between uploading image and the 'Analyze' button."
*   **Performance:** "Analysis speed is faster than expected (approx. 10ms inference)."

**Iteration Based on Feedback:**
*   Improvements were made to the UI to clearly distinguish the "Upload" action from the "Start Analysis" trigger.
*   Tooltips were added to explain the metric units (hectares vs acres).

### 4.4.2 TEST CASES

**Test Case 1: Registration with Valid Input**
| Field | Description |
| :--- | :--- |
| **Test Case ID** | TC_REG_001 |
| **Related Feature ID** | AUTH_01 (User Registration) |
| **Objective** | Verify that a new user can successfully register with valid details. |
| **Test Coverage** | `app.py` - `/register` route, `User` model insertion. |
| **Steps** | 1. Navigate to the Registration page.<br>2. Enter a valid Name (e.g., "Ali").<br>3. Enter a valid Email (e.g., "ali@example.com").<br>4. Enter a Password (min 8 chars).<br>5. Confirm Password.<br>6. Click "Register". |
| **Expected Result** | User is redirected to the Dashboard; Data is saved in the database. |
| **Actual Result** | User was redirected to Dashboard; New row appeared in Users table. |
| **Pass/Fail** | **PASS** |

**Test Case 2: Login with Invalid Credentials**
| Field | Description |
| :--- | :--- |
| **Test Case ID** | TC_LOG_002 |
| **Related Feature ID** | AUTH_02 (User Login) |
| **Objective** | Ensure the system denies access for incorrect passwords. |
| **Test Coverage** | `app.py` - `/login` route, password hashing check. |
| **Steps** | 1. Navigate to Login page.<br>2. Enter registered email "ali@example.com".<br>3. Enter wrong password "wrongpass123".<br>4. Click "Login". |
| **Expected Result** | System displays "Invalid credentials" flash message; Access denied. |
| **Actual Result** | Error message displayed; User remained on Login page. |
| **Pass/Fail** | **PASS** |

**Test Case 3: Image Upload & Analysis**
| Field | Description |
| :--- | :--- |
| **Test Case ID** | TC_PROC_001 |
| **Related Feature ID** | CORE_01 (Image Processing) |
| **Objective** | Verify that an uploaded image is processed and returns results. |
| **Test Coverage** | `app.py` `/upload`, `inference.py` YOLOv8 pipeline. |
| **Steps** | 1. Log in to the application.<br>2. Navigate to "Upload" page.<br>3. Select a valid `.jpg` drone image.<br>4. Click "Analyze". |
| **Expected Result** | Processing spinner appears; User is redirected to Result page showing counts and marked image. |
| **Actual Result** | Analysis completed; Count: 124 Trees found; Charts rendered. |
| **Pass/Fail** | **PASS** |

---

# CHAPTER FIVE: CONCLUSION

## 5.1 Project Requirements
The development of PalmaCount required a robust set of hardware and software components to handle computer vision tasks efficiently.
*   **Hardware:** Development was conducted on a machine equipped with a discrete GPU (NVIDIA RTX series) to accelerate YOLOv8 training and inference.
*   **Software:** The core stack included Python 3.9+, PyTorch for tensor operations, and OpenCV for image manipulation.
*   **Data:** A dataset of annotated aerial imagery (oil palm plantations) was essential for training the deep learning model to varying environmental conditions.

## 5.2 Project Constraints
*   **Computational Resources:** High-resolution drone imagery (often 4K+) requires significant RAM and processing power. The system implements image resizing and optimization to function within the constraints of standard web hosting tiers (e.g., Render Free Tier limitations).
*   **Network Dependency:** As a web-based system, the speed of uploading large image files is dependent on the user's internet bandwidth.
*   **Environmental Variability:** The model's accuracy can be slightly affected by extreme lighting conditions (heavy shadows or overexposure) in the input imagery.

## 5.3 Future Enhancement
For future enhancement, a **Mobile Application** version of PalmaCount could be developed. This would facilitate users, particularly field officers, to:
1.  Capture images directly via the mobile camera or connected drone controller.
2.  Track and view analyzed images on-site without needing a laptop.
3.  Utilize GPS features to tag specific tree locations for ground verification.
4.  Implement "Offline Mode" to allow data collection in remote areas with poor connectivity, syncing later when online.

## 5.4 Conclusion
In conclusion, the PalmaCount project successfully demonstrates the viability of using deep learning for precision agriculture in the palm oil industry. By automating the tedious task of tree counting, the system not only saves significant manual labor hours but also provides consistency and accuracy that exceeds human capability in large-scale scenarios. Integrating this AI capability into a user-friendly web platform ensures that the technology is accessible to plantation managers regardless of their technical expertise. This project lays a strong foundation for future advancements in automated plantation management and intelligent yield estimation.
