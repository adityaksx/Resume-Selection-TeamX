"""Generate realistic synthetic resumes to bring candidate pool to 18 resumes for Phase 7 validation."""

from __future__ import annotations

import os
import fitz

RESUMES_DIR = os.path.join("data", "resumes")
os.makedirs(RESUMES_DIR, exist_ok=True)

def create_pdf(text: str, filename: str) -> None:
    filepath = os.path.join(RESUMES_DIR, filename)
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(54, 54, 550, 750)
    page.insert_textbox(rect, text, fontsize=10)
    doc.save(filepath)
    doc.close()
    print(f"Created: {filepath}")

# 15 additional resumes to complement Rahul Sharma, Alex Rivera, and Sara Chen
RESUMES_DATA = [
    # 4. Priya Patel (Strong Full Stack with aliases)
    (
        "Priya_Patel_Resume.pdf",
        """Priya Patel
priya.patel@example.com | (555) 234-5678 | San Jose, CA
github.com/priyapatel | linkedin.com/in/priyapatel

Technical Skills:
Languages: JavaScript, TypeScript, HTML5, CSS3
Frameworks: ReactJS, NodeJS, Express.js
Databases & Tools: Mongo DB, Docker, Git, RESTful API

Experience:
Full Stack Software Intern at CloudTech Labs | Jun 2023 - Dec 2023
• Developed and deployed RESTful APIs using NodeJS and Express.
• Designed database collections and aggregation pipelines in Mongo DB.
• Implemented interactive stateful UI components using ReactJS.
• Collaborated with remote development teams using Git.

Projects:
Microservices Dashboard | ReactJS, NodeJS, Docker
• Built real-time monitoring dashboard with containerized services.
• Integrated RESTful endpoints for telemetry data.

Education:
B.S. in Computer Science, San Jose State University | 2021 - 2025
""",
    ),
    # 5. Marcus Vance (Backend Developer - lacks React)
    (
        "Marcus_Vance_Resume.pdf",
        """Marcus Vance
marcus.vance@example.com | (555) 345-6789 | Austin, TX

Technical Skills:
Languages & Backend: Node.js, Express, Python, SQL
Databases: MongoDB, PostgreSQL, Redis
DevOps: Docker, Git, Linux, REST API

Experience:
Backend Developer Intern at DataPulse | Jan 2024 - Present
• Designed secure REST APIs with Node.js and Express for payment processing.
• Optimized query performance on MongoDB database clusters.
• Configured automated deployment containers with Docker.
• Managed branching and merge requests via Git.

Projects:
API Gateway Service | Node.js, MongoDB, Redis
• Scalable reverse proxy and rate limiting gateway for microservices.

Education:
B.S. in Software Engineering, University of Texas at Austin | 2020 - 2024
""",
    ),
    # 6. Elena Rostov (DevOps / Cloud - lacks core web dev)
    (
        "Elena_Rostov_Resume.pdf",
        """Elena Rostov
elena.rostov@example.com | (555) 456-7890 | Seattle, WA

Technical Skills:
Cloud & Infrastructure: AWS, Docker, Kubernetes, Terraform, Linux
Tools: Git, Jenkins, Prometheus, Bash, Go

Experience:
Cloud Infrastructure Intern at OrbitScale | May 2023 - Nov 2023
• Provisioned and automated cloud infrastructure on AWS using Terraform.
• Packaged backend services into Docker containers deployed on Kubernetes.
• Maintained infrastructure as code repositories with Git.

Certifications:
• AWS Certified Solutions Architect Associate

Education:
B.S. in Information Technology, University of Washington | 2020 - 2024
""",
    ),
    # 7. David Kim (Frontend Specialist - lacks Node/MongoDB)
    (
        "David_Kim_Resume.pdf",
        """David Kim
david.kim@example.com | (555) 567-8901 | New York, NY

Technical Skills:
Frontend: React, TypeScript, Redux, JavaScript, HTML5, CSS3, Tailwind CSS
Tools: Git, Webpack, Vite, Figma

Experience:
Frontend Web Intern at PixelCraft Media | Jun 2023 - Present
• Engineered responsive web applications using React and TypeScript.
• Built component design systems with modern CSS and Tailwind.
• Managed codebase version control using Git.

Projects:
Design System Showcase | React, TypeScript
• Reusable UI component library tested across modern web browsers.

Education:
B.A. in Computer Science, New York University | 2021 - 2025
""",
    ),
    # 8. Aisha Khan (Full Stack with Cloud - Strong match)
    (
        "Aisha_Khan_Resume.pdf",
        """Aisha Khan
aisha.khan@example.com | (555) 678-9012 | Chicago, IL

Technical Skills:
Web Technologies: React, Node.js, Express, MongoDB, REST API, JavaScript
Cloud & Tools: AWS, Git, Postman, TypeScript, Docker

Experience:
Software Engineering Intern at NextEra Solutions | Jun 2023 - Dec 2023
• Built scalable REST APIs using Node.js and Express backed by MongoDB.
• Implemented user authentication and responsive dashboards using React.
• Deployed serverless microservices to AWS cloud infrastructure.
• Collaborated in an agile scrum team using Git for version control.

Projects:
TaskFlow Pro | React, Node.js, MongoDB, AWS
• Collaborative task tracking platform deployed with Docker and AWS S3.

Education:
B.S. in Computer Science, University of Illinois Urbana-Champaign | 2021 - 2025
""",
    ),
    # 9. Liam O'Connor (Mobile Developer - React Native false positive check)
    (
        "Liam_OConnor_Resume.pdf",
        """Liam O'Connor
liam.oconnor@example.com | (555) 789-0123 | Boston, MA

Technical Skills:
Mobile: React Native, Swift, Kotlin, iOS, Android
Languages: JavaScript, TypeScript, Objective-C
Tools: Git, Xcode, Android Studio

Experience:
Mobile Application Intern at AppForge | May 2023 - Jan 2024
• Developed cross-platform mobile applications using React Native.
• Published production native apps to Apple App Store and Google Play.
• Tracked issues and managed feature branches using Git.

Projects:
FitTrack Mobile | React Native, TypeScript
• Mobile fitness tracking application with local offline storage.

Education:
B.S. in Computer Engineering, Northeastern University | 2020 - 2024
""",
    ),
    # 10. Suresh Menon (Java Enterprise - Java vs JS false positive check)
    (
        "Suresh_Menon_Resume.pdf",
        """Suresh Menon
suresh.menon@example.com | (555) 890-1234 | Atlanta, GA

Technical Skills:
Backend & Enterprise: Java, Spring Boot, Hibernate, Apache Kafka
Databases: Oracle SQL, PostgreSQL
Tools: Git, Maven, Docker, Linux

Experience:
Enterprise Java Intern at FinServe Corp | Jun 2023 - Dec 2023
• Built high-throughput transaction processing systems using Java and Spring Boot.
• Designed relational database schemas in Oracle SQL.
• Maintained code quality and Git repository workflows.

Education:
B.S. in Computer Science, Georgia Institute of Technology | 2021 - 2025
""",
    ),
    # 11. Zoe Castillo (Systems C Programmer - C vs C++ false positive check)
    (
        "Zoe_Castillo_Resume.pdf",
        """Zoe Castillo
zoe.castillo@example.com | (555) 901-2345 | Boulder, CO

Technical Skills:
Systems Programming: C, Linux Kernel, Assembly x86, POSIX Threads
Tools: Git, GCC, GDB, Valgrind, Make

Experience:
Systems Programming Intern at EmbeddedEdge | Jun 2023 - Aug 2023
• Developed low-level hardware drivers and memory managers in pure C.
• Debugged race conditions and memory leaks using Valgrind and GDB.
• Maintained firmware codebases using Git.

Education:
B.S. in Computer Engineering, University of Colorado Boulder | 2021 - 2025
""",
    ),
    # 12. Ananya Deshmukh (Full Stack Junior - Matches all required, lacks preferred)
    (
        "Ananya_Deshmukh_Resume.pdf",
        """Ananya Deshmukh
ananya.deshmukh@example.com | (555) 012-3456 | Dallas, TX

Technical Skills:
Web Development: React, Node.js, MongoDB, REST API, Git, JavaScript, HTML, CSS

Experience:
Web Development Intern at TechStarters | Jan 2024 - Present
• Developed interactive web applications with React frontend.
• Built REST API endpoints with Node.js and Express.
• Created schemas and handled data storage using MongoDB.
• Collaborated with developers using Git version control.

Education:
B.S. in Information Systems, University of Texas at Dallas | 2022 - 2026
""",
    ),
    # 13. Brandon Taylor (Cloud Infra Azure - AWS vs Azure false positive check)
    (
        "Brandon_Taylor_Resume.pdf",
        """Brandon Taylor
brandon.taylor@example.com | (555) 123-9876 | Phoenix, AZ

Technical Skills:
Cloud: Azure, Azure DevOps, Terraform, PowerShell, Docker
Tools: Git, Active Directory, Bash

Experience:
Cloud Systems Intern at SkyNet Infotech | May 2023 - Present
• Automated virtual network deployments in Microsoft Azure cloud.
• Managed CI/CD release pipelines with Azure DevOps and Docker.
• Version-controlled deployment scripts with Git.

Certifications:
• Microsoft Certified: Azure Fundamentals

Education:
B.S. in Cloud Computing, Arizona State University | 2021 - 2025
""",
    ),
    # 14. Fatima Al-Mansoor (Web Developer - Git vs GitHub check)
    (
        "Fatima_Al_Mansoor_Resume.pdf",
        """Fatima Al-Mansoor
fatima.almansoor@example.com | (555) 234-8765 | Los Angeles, CA

Technical Skills:
Web: React, Node.js, Express, MongoDB, REST API, JavaScript
Platforms & Tools: GitHub, Docker, Postman, CSS3

Experience:
Web Engineering Intern at Sunset Media | Jun 2023 - Dec 2023
• Built client web applications with React and REST API backends.
• Managed MongoDB collections and wrote Express route controllers.
• Maintained open source repositories and pull requests on GitHub.

Education:
B.S. in Computer Science, University of California, Los Angeles | 2021 - 2025
""",
    ),
    # 15. Oliver Smith (Full Stack with TypeScript & Docker - High match)
    (
        "Oliver_Smith_Resume.pdf",
        """Oliver Smith
oliver.smith@example.com | (555) 345-7654 | Portland, OR

Technical Skills:
Full Stack: React, Node.js, Express, MongoDB, REST API, TypeScript, Docker, Git

Experience:
Full Stack Intern at Cascade Software | Jun 2023 - Present
• Developed modular microservices using Node.js, Express, and TypeScript.
• Built high-performance responsive user interfaces using React.
• Structured document models in MongoDB and authored REST APIs.
• Containerized development environments using Docker and tracked via Git.

Projects:
AgileSprint Manager | React, Node.js, MongoDB, TypeScript, Docker
• Team task management web application with containerized architecture.

Education:
B.S. in Computer Science, Oregon State University | 2021 - 2025
""",
    ),
    # 16. Maya Lin (Graphic & UI/UX Designer - Minimal technical match)
    (
        "Maya_Lin_Resume.pdf",
        """Maya Lin
maya.lin@example.com | (555) 456-6543 | San Francisco, CA

Technical Skills:
Design & Media: Figma, Adobe XD, Photoshop, Illustrator, InDesign, Wireframing
Web Basics: HTML, CSS

Experience:
UI/UX Design Intern at StudioCreative | May 2023 - Present
• Designed user interface mockups, wireframes, and prototypes in Figma.
• Created marketing graphics, brand assets, and digital illustrations.
• Conducted user research interviews and usability testing sessions.

Education:
B.F.A. in Graphic Design, California College of the Arts | 2020 - 2024
""",
    ),
    # 17. Carlos Mendoza (Backend Python - Lacks React, Node, Mongo)
    (
        "Carlos_Mendoza_Resume.pdf",
        """Carlos Mendoza
carlos.mendoza@example.com | (555) 567-5432 | Denver, CO

Technical Skills:
Backend & Data: Python, Django, FastAPI, PostgreSQL, Redis, REST API
Tools: Git, Linux, Docker, Celery

Experience:
Backend Engineering Intern at MileHigh Tech | Jun 2023 - Dec 2023
• Built asynchronous REST API microservices with Python and FastAPI.
• Optimized relational database queries and indices in PostgreSQL.
• Collaborated on feature development using Git branching strategies.

Projects:
FastReport API | Python, FastAPI, PostgreSQL
• Automated analytics service processing streaming events.

Education:
B.S. in Computer Science, University of Colorado Denver | 2021 - 2025
""",
    ),
    # 18. Nina Ivanova (Full Stack with ReactJS variant & AWS - High match)
    (
        "Nina_Ivanova_Resume.pdf",
        """Nina Ivanova
nina.ivanova@example.com | (555) 678-4321 | Philadelphia, PA

Technical Skills:
Languages & Web: JavaScript, TypeScript, ReactJS, Node.js, REST API
Databases & Cloud: MongoDB, AWS, Git, Express.js

Experience:
Full Stack Developer Intern at Keystone Technologies | Jun 2023 - Dec 2023
• Engineered scalable REST API endpoints using Node.js and Express.
• Designed and maintained data schemas using MongoDB.
• Created dynamic, accessible user interfaces with ReactJS.
• Deployed web applications to AWS cloud infrastructure and managed code with Git.

Certifications:
• AWS Certified Cloud Practitioner

Education:
B.S. in Software Engineering, Drexel University | 2021 - 2025
""",
    ),
]

for filename, text in RESUMES_DATA:
    create_pdf(text, filename)

print(f"Successfully generated {len(RESUMES_DATA)} additional resumes. Total resumes in {RESUMES_DIR}: {len(os.listdir(RESUMES_DIR))}")
