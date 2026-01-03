
# CHAPTER FOUR: PROJECT DEVELOPMENT, IMPLEMENTATION AND EVALUATION

## 4.1 Introduction
This chapter covers the implementation and integration of the PalmaCount system, detailing the interactions between the frontend interface, the backend logic, and the database management system. It outlines the tools, frameworks, and methodologies utilized to ensure a seamless transition from design to valid deployment. Furthermore, this chapter highlights the evaluation of the system through rigorous testing phases to ensure robustness and user satisfaction.

## 4.2 System Integration
The integration of frontend, backend, and database in PalmaCount was designed to ensure a smooth working flow between components, real-time analysis, and a seamless user experience. The system adopts a service-oriented architecture where the user interactive layer is decoupled from the heavy computational AI layer.

### Frontend and Backend Integration
Technology Stack:
*   Frontend: Flask (Python web framework) that includes Hypertext Markup Language (HTML), Cascading Style Sheets (CSS), and Tailwind CSS for styling.
*   Backend: Deep learning model YOLOv8 hosted on a separate FastAPI service.

How Integration Works:
The integration works through RESTful API communication. When a user uploads an image on the Flask frontend:
1.  Request Generation: The Flask application receives the image file and validates it. It then constructs a multipart HTTP POST request containing the image data.
2.  API Call: This request is sent asynchronously to the FastAPI backend (/predict endpoint).
3.  Inference & Response: The backend processes the image using the YOLOv8 model (inference.py), generates the tree counts, area calculations, and annotated visualizations. These results are packaged into a JSON object and returned to the Flask frontend.
4.  Rendering: The Flask frontend parses this JSON response and dynamically renders the results using Jinja2 templates (analysis_detail.html) to display the detected trees and statistics to the user.

### Backend and Database Integration
Database:
*   System: PostgreSQL (Production) / SQLite (Development).
*   ORM: SQLAlchemy is used to manage database interactions, allowing for structured data storage including user profiles and complex analysis records.

How Integration Works:
The backend interacts with the database using an Object-Relational Mapper (ORM):
1.  Data Modeling: Python classes (User and Analysis) are defined to represent database tables.
2.  Persistence: When an analysis is successfully completed, the Flask backend creates a new Analysis object containing the mature_count, young_count, total_area, and file paths.
3.  Transaction: This object is added to the database session and committed (db.session.commit()), effectively saving the record permanently in the relational table linked to the specific user's ID.

### Frontend and Database Direct Integration
Authentication:
*   Mechanism: Users log in or register via the Flask application, which utilizes Werkzeug for password hashing and Flask-Login for session management.
*   Process:
    *   Registration: The frontend sends user input (name, email, password) to the backend. The backend hashes the password for security and inserts a new row into the users table.
    *   Login: Upon successful credential validation, the server creates a secure session cookie (user_id). The frontend uses this session to identify the user in subsequent requests, allowing access to protected routes like the Dashboard.

Recent Image Analysis:
The system ensures users can access their data history instantaneously:
*   Retrieval: When a user accesses the "History" or "Dashboard" page, the frontend requests data from the backend.
*   Querying: The backend performs a database query (Analysis.query.filter_by(user_id=session['user_id'])) to fetch only the analyses belonging to that specific user.
*   Display: These records are passed to the frontend templates, allowing the user to view a list of their recent uploads and click on them to view the full detailed reports.

## 4.3 System Output
The PalmaCount system processes the input imagery and generates a comprehensive analysis report. This output is designed to provide immediate, actionable agronomic data to the user.

Display Final Output Integration:
Upon successful analysis, the user is presented with the Analysis Detail Dashboard, which includes:
1.  Annotated Visuals: The original drone image is overlaid with color-coded bounding boxes.
    *   Green/Yellow/Red Boxes: Represent "Mature" palms (Healthy, Yellowing, or Dead).
    *   Light Green Boxes: Represent "Young" palms.
2.  Statistical Summary: A real-time data table displaying:
    *   Total Tree Count: The sum of all detected oil palms.
    *   Maturity Breakdown: Segregated counts for Mature vs. Young trees.
    *   Area Estimation: The calculated canopy coverage in both square meters (m^2) and hectares (ha), derived using the "Geometric: multiple_radii" method as defined in the system's inference logic.
3.  Data Visualization:
    *   Composition Chart: A donut chart visualizing the ratio of mature to young trees.
    *   Crown Size Histogram: A graph showing the distribution of tree canopy sizes, allowing for the identification of growth uniformity across the plantation.

(Figure 4.1: Example of System Output showing detected trees and statistics)
> [Place Final Output Image Here]

## 4.4 System Testing
System testing was conducted to verify that individual functions, classes, and microservices interact correctly to meet the project requirements.

### 4.4.1 User Acceptance Testing (UAT)
UAT was performed to ensure the application aligns with end-user expectations and is ready for deployment.

End User Participation:
*   Participants: Conducted sessions with potential users (e.g., estate managers, agricultural officers).
*   Tasks Performed: Users were asked to execute the following workflows:
    1.  Registration & Onboarding: Creating a new account and setting up a profile.
    2.  Authentication: Logging in securely.
    3.  Operational Use: Uploading a sample drone image and initiating the analysis.
    4.  Review: Interpreting the results on the dashboard.

Feedback Collection:
*   Usability: "The interface is clean; the distinction between mature and young trees is very useful for planning replanting."
*   Performance: "The analysis speed is impressive, taking less than 10 seconds for a standard tile."
*   Suggestions: Some users initially found the area metric (sq meters vs hectares) confusing, leading to the addition of clearer labels in the final UI.

Iteration Based on Feedback:
*   Based on user inputs, the "History" page was enhanced to sort analyses by date, ensuring users can easily find their most recent work.
*   Tooltips were added to explain the metric units.

### 4.4.2 TEST CASES

Test Case 1: User Registration
| Field | Description |
| :--- | :--- |
| Test Case ID | TC_AUTH_01 |
| Related Feature ID | User Account Management |
| Objective | Verify that a new user can register with a unique email address. |
| Test Coverage | User Model, /register endpoint |
| Steps | 1. Navigate to /register.<br>2. Enter Name: "Tester".<br>3. Enter Email: "test@palmacount.com".<br>4. Enter Password: "Password123".<br>5. Click "Register". |
| Expected Result | Account is created, hashed password is stored in DB, and user is redirected to Dashboard. |
| Actual Result | User successfully redirected to Dashboard; DB record created. |
| Pass/Fail | PASS |

Test Case 2: Image Analysis Pipeline
| Field | Description |
| :--- | :--- |
| Test Case ID | TC_CORE_02 |
| Related Feature ID | Deep Learning Inference |
| Objective | Ensure uploaded image returns correct bounding box data and counts. |
| Test Coverage | /upload route, inference.py service associated with YOLOv8. |
| Steps | 1. Login as valid user.<br>2. Upload sample_drone_img.jpg.<br>3. Click "Analyze". |
| Expected Result | System returns JSON with total_count > 0, image_base64 string, and renders the result page. |
| Actual Result | Analysis ID generated; Result page displayed with 124 trees detected. |
| Pass/Fail | PASS |

Test Case 3: History Retrieval
| Field | Description |
| :--- | :--- |
| Test Case ID | TC_DATA_03 |
| Related Feature ID | Data Persistence & History |
| Objective | Verify that past analyses are saved and retrievable by the specific user. |
| Test Coverage | /history route, Database Querying |
| Steps | 1. Navigate to "History" page.<br>2. Check for the analysis performed in TC_CORE_02. |
| Expected Result | The list should display the recently analyzed image with correct timestamp and tree count. |
| Actual Result | Recent analysis displayed at the top of the list. |
| Pass/Fail | PASS |

---

# CHAPTER FIVE: CONCLUSION

## 5.1 Project Requirements
The development of PalmaCount required a robust set of hardware and software components to handle computer vision tasks efficiently.
*   Hardware: Development was conducted on a machine equipped with a discrete GPU (NVIDIA RTX series) to accelerate YOLOv8 training and inference.
*   Software: The core stack included Python 3.9+, PyTorch for tensor operations, and OpenCV for image manipulation.
*   Data: A dataset of annotated aerial imagery (oil palm plantations) was essential for training the deep learning model to varying environmental conditions.

## 5.2 Project Constraints
*   Computational Resources: High-resolution drone imagery (often 4K+) requires significant RAM and processing power. The system implements image resizing and optimization to function within the constraints of standard web hosting tiers (e.g., Render Free Tier limitations).
*   Network Dependency: As a web-based system, the speed of uploading large image files is dependent on the user's internet bandwidth.
*   Environmental Variability: The model's accuracy can be slightly affected by extreme lighting conditions (heavy shadows or overexposure) in the input imagery.

## 5.3 Future Enhancement
For future enhancement, a Mobile Application version of PalmaCount could be developed. This would facilitate users, particularly field officers, to:
1.  Capture images directly via the mobile camera or connected drone controller.
2.  Track and view analyzed images on-site without needing a laptop.
3.  Utilize GPS features to tag specific tree locations for ground verification.
4.  Implement "Offline Mode" to allow data collection in remote areas with poor connectivity, syncing later when online.

## 5.4 Conclusion
In conclusion, the PalmaCount project successfully demonstrates the viability of using deep learning for precision agriculture in the palm oil industry. By automating the tedious task of tree counting, the system not only saves significant manual labor hours but also provides consistency and accuracy that exceeds human capability in large-scale scenarios. Integrating this AI capability into a user-friendly web platform ensures that the technology is accessible to plantation managers regardless of their technical expertise. This project lays a strong foundation for future advancements in automated plantation management and intelligent yield estimation.
