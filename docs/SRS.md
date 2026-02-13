Syllabify
Andrew Martin, Leon Wong, Kenny Nguyen, Saint George Aufranc
Software Requirements Specification Template
How to use this document: Keep the headings and document structure. Replace or modify the text within each section with the content described. Optionally add another level of structure in Section 2 to organize requirements around major user activities or system behaviors. The final SRS should be self-contained, clearly describing what the document is, who wrote each section, and when. Each section must specify who wrote it and when.
Delete all red text before submitting.
1. The Concept of Operations (ConOps)

The concept of operations (ConOps) "describes system characteristics for a proposed system from the users' viewpoint" (IEEE Std 1362-1998). The ConOps communicates overall system characteristics to all stakeholders and should be readable by any stakeholder familiar with the application domain. It clarifies the software's context and the capabilities the system will provide (Faulk, 2017).
Include all sections described below. For small systems, Sections 1.1 through 1.5 may contain only one or two paragraphs each. The Use Cases in Section 1.6 should be more detailed.
Additional ConOps sections are described in IEEE Std 1362-1998 Section 4 at https://ieeexplore.ieee.org/document/761853.
1.1 Current System or Situation [Andrew Martin - February 05, 2026]
	Currently, students manage academic deadlines by manually gathering information from each course. For each class, a student typically navigates to the course’s Canvas page or class website to get to their syllabus, then they search for the assignment deadlines, exam dates, and course schedules. Syllabi can vary widely in format and file type, including PDF, Canvas pages, class websites, and text files. A student will review this information and then manually enter the important dates into their own calendars.
	Even when Canvas shows due dates, students must still manage their own schedules while accounting for the time assignments or studying for a test may require. This leads to an inflexible process that relies on the student to accurately transcribe their schedules or on an AI assistant to detect important dates without hallucination. At best, these approaches are time-consuming, and at worst, they are inaccurate.

1.2 Justification for a New System
The current system requires students to manually consolidate syllabus information and convert deadlines into a workable plan. In an Inside Higher Ed/ College Pulse Student Voice survey of over 3000 two and four years college students writes “The top resource respondents said would improve their time management was the ability to combine different syllabi to organize deadlines.” With 40% saying that this was their most pressing issue.
According to research conducted by educationaldatamining.org, most students complete and submit their class work very close to the deadline. One Educational Data Mining conference paper reports that more that 60% of students did not submit assignments until the last 24 hours before the deadline. If left on there own the majority of students will procrastinate, which is why a system that wold manage their time for them would increase there performance.
1.3 Operational Features of the Proposed System
Briefly describe what the new system will do. "This section describes the critical operational features—the essential services and constraints—of the proposed system at a high level without specifying design details. The description should clearly explain how the system meets users' needs and addresses the shortcomings of the current system. In some cases, to clarify operational details, it may be necessary to suggest possible design details, such as design strategies or specific implementations. Make clear that these are not committed design specifications" (IEEE Std 1362-1998).
1.4 User Classes
Briefly describe each user class for the proposed system. A user class is a group of users who interact with the system in similar ways (e.g., students, instructors, system administrators, publishers, programmers, installers). Factors distinguishing user classes include common responsibilities, skill levels, work activities, and system interaction modes. Different user classes may have distinct operational scenarios. Users include anyone who interacts with the system, including operational users, data-entry personnel, system operators, support personnel, software maintainers, and trainers (IEEE Std 1362-1998).
1.5 Modes of Operation [Kenny Nguyen - Jan 31, 2026]
Syllabify uses several modes of operation that interact with user role, authentication state, and system availability (IEEE Std 1362-1998). Unauthenticated mode restricts access to the login page only. Users need to provide valid credentials to proceed past the login page. After the login page, there is a first-time setup mode that only applies to newly registered users who have just created their account and have not completed creating their security questions and answers. They are directed to the security setup flow before accessing the main dashboard. Student mode is the primary mode for students, which are our end users. In this mode, students receive full access to syllabus upload, parsing, data review, schedule generation, and calendar export. Administrator mode is for developers and system administrators. Administrators have higher permissions than students and access a separate admin interface for user management, system configuration, and maintenance operations that normal users don’t see. Maintenance mode can be activated by an administrator for updates, apply patches, or address issues. During maintenance, students may be restricted or the system may display a maintenance notice. In degraded mode (i.e. when parsing fails, the backend is unavailable, or schedule generation encounters errors), the system displays clear error messages and allows the user to retry, edit inputs, or navigate elsewhere rather than blocking entirely.
1.6 Operational Scenarios (Use Cases) [Kenny Nguyen - Jan 31, 2026]
An operational scenario [Use Case] is a step-by-step description of how the proposed system should operate and interact with its users and external interfaces under a given set of circumstances. Describe scenarios so readers can walk through them and understand how all parts of the system function and interact. The scenarios tie together all parts of the system, users, and other entities by describing how they interact. The following use cases follow a structured format for clarity (Cockburn, 2001; Oracle, 2007).
Use Case 1: User Login
Brief description: This use case describes how a student or administrator authenticates to access Syllabify.
Actors: A student and/or administrator (developer or system admin).
Preconditions: 
The user has a registered account with a username and password.
The user has access to the Syllabify web application.
Steps to Complete the Task: 
The user opens the Syllabify application in a web browser.
The system displays the login page.
The user enters their username and password.
The user submits the login form.
The system validates credentials and returns a JWT.
If:
Administrator: The system redirects to the admin interface.
Student (security setup complete): The system redirects to the dashboard.
Student (first-time): The system redirects to the security setup page.
Postconditions: The user is authenticated; a valid token is stored; the user is directed to the appropriate interface based on role.

Use Case 2: Security Setup (First-Time)
Brief description: This use case describes how a new user completes one-time security questions before accessing the main application.
Actors: A student (first-time user).
Preconditions: 
The student has logged in successfully.
The student has not yet completed security setup.
The system has redirected the student to the security setup page.
Steps to Complete the Task: 
The system displays the security setup form with configurable questions.
The student answers each security question.
The student submits the form.
The system stores the hashed answers and marks security setup as complete.
The system redirects the student to the dashboard.
Postconditions: The student has completed security setup; they can access the full application; security answers are stored for account recovery.

Use Case 3: Upload and Parse Syllabus
Brief description: This use case describes how a student uploads a syllabus (PDF or plaintext) and the system extracts assignments and due dates.
Actors: A student.
Preconditions: 
The student is authenticated and has completed security setup.
The student has a syllabus available (PDF file or text that can be pasted).
Steps to Complete the Task: 
The student navigates to the Upload page.
The student chooses to upload a PDF or paste syllabus text.
If:
PDF: The student selects a file and uploads it; the system extracts text from the PDF.
Paste: The student pastes syllabus text into the input area.
The student submits the content for parsing.
The system returns the parsed data (assignments with names, due dates, estimated hours).
The system returns the parsed data (assignments with names, due dates, estimated hours).
Postconditions: Parsed assignment data is available for review; the student proceeds to the data review step. If parsing fails, the system shows an error and allows retry.

Use Case 4: Review and Confirm Parsed Data
Brief description: This use case describes how a student reviews, edits, and confirms the extracted syllabus data before schedule generation.
Actors: A student.
Preconditions: 
Parsed assignment data is available from the previous use case.
The student is on the Upload page in the review step.
Steps to Complete the Task: 
The system displays the parsed assignments in an editable table (name, due date, estimated hours).
The student reviews the extracted data.
The student may add, edit, or remove assignments to correct errors.
The student confirms the data is accurate.
The system saves the course and assignment data.
Postconditions: The course and assignments are stored; the student can generate a schedule or add more courses.

Use Case 5: Generate and Approve Study Schedule
Brief description: This use case describes how a student generates a proposed study schedule and approves it before export.
Actors: A student.
Preconditions: 
The student has at least one course with confirmed assignments.
The student has set preferences (work hours, preferred days) in the Preferences page, or defaults apply.
Steps to Complete the Task: 
The student navigates to the Schedule page.
The student selects one or more courses to include.
The student initiates schedule generation.
The system applies heuristics (deadlines, workload, preferences) to allocate time blocks.
The system returns a proposed schedule and displays it in a weekly grid.
The student reviews the proposed schedule.
The student approves the schedule (user confirmation is required before export).
Postconditions: An approved schedule exists; the student can export it to a calendar. The system does not export without explicit user approval.

Use Case 6: Export Schedule to Calendar
Brief description: This use case describes how a student exports an approved schedule to Google Calendar or downloads an ICS file.
Actors: A student.
Preconditions: 
The student has an approved schedule.
The student has navigated to the export option.
Steps to Complete the Task: 
The student chooses to export (Google Calendar or ICS download).
If:
Google Calendar: The student authenticates with Google OAuth if needed; the system pushes events to their calendar.
ICS: The system generates an ICS file; the student downloads it.
The system confirms successful export.
Postconditions: The schedule events appear in the student's calendar; the student can view and manage them in their preferred calendar application.

Use Case 7: Administrator Performs System Maintenance
Brief description: This use case describes how an administrator views and manages user accounts.
Actors: An administrator (developer or system admin).
Preconditions: 
The administrator is authenticated and has admin privileges.
The system is not in maintenance mode (or the administrator has maintenance bypass).
Steps to Complete the Task: 
The administrator accesses the admin interface and navigates to user management.
The system displays a list of registered users.
The administrator may search, filter, or sort users.
The administrator may view user details, disable an account, or reset a user's security setup status as needed.
The administrator confirms any changes.
The system applies the changes and updates the user records.
Postconditions: User account status is updated; affected users are subject to the new permissions or restrictions.

Use Case 8: Administrator Performs System Maintenance
Brief description: This use case describes how an administrator enters maintenance mode, performs updates, and restores normal operation.
Actors: An administrator (developer or system admin).
Preconditions: 
The administrator is authenticated and has admin privileges.
Steps to Complete the Task: 
The administrator accesses the admin interface and selects the option to enter maintenance mode.
The administrator may specify a maintenance message to display to students.
The system enables maintenance mode; students see the maintenance notice or are restricted from certain operations.
The administrator performs updates, patches, or other maintenance tasks.
The administrator selects the option to exit maintenance mode.
The system restores normal operation; students regain full access.
Postconditions: Maintenance is complete; the system operates normally; students can access all features.

See the Oracle (2007) White Paper on "Getting Started With Use Case Modeling" at: https://www.oracle.com/technetwork/testcontent/gettingstartedwithusecasemodeling-133857.pdf
Diagrams can assist communication. "Graphical tools should be used wherever possible, especially since ConOps documents should be understandable by several different types of readers. Useful graphical tools include work breakdown structures (WBS), N2 charts, sequence or activity charts, functional flow block diagrams, structure charts, allocation charts, data flow diagrams (DFD), object diagrams, context diagrams, storyboards, and entity-relationship diagrams" (IEEE Std 1362-1998).
2. Specific Requirements
This section specifies the actual requirements. A requirement describes a behavior or property that a computer program must have, independent of how it is achieved. Requirements must be complete, unambiguous, consistent, and objectively verifiable (Sethi, Chapter 3). Requirements describe what the system will do but do not commit to specific design details.
Organize requirements in a hierarchy to make them easier to read, understand, modify, and find. The following section headings provide one way to organize requirements (adapt as needed). Sections 2.1, 2.2, 2.3, and 2.4 describe "behavioral requirements" (Faulk, 2013). If a system supports two major user activities, describe behavioral requirements for each activity separately.
Distinguish between "functional" and "non-functional" requirements. Functional requirements describe services provided by the system; non-functional requirements describe constraints on the system and its development.
Whenever possible, prioritize requirements using the MoSCoW categories: Must have, Should have, Could have, and Won't have (Sethi, p. 110). Group requirements by priority for clarity.
Use indented, numbered lists for requirements:
General Requirement
Specific Requirement
Requirement Detail
This numbering scheme permits reference to other parts of the document, e.g., SRS 1.1.1.
2.1 External Interfaces (Inputs and Outputs)
Describe inputs into and outputs from the software system (ISO/IEC/IEEE 29148:2018). This section documents how the system exchanges data with external entities (users, other systems, hardware, and databases). This defines the system’s boundaries and interactions.
For each interface, specify:
Name of item — Clear identifier (e.g., "User Login Credentials", "Payment API Response")
Description of purpose — What the interface does and why it exists
Source of input or destination of output
Inputs: Where data comes from (user, external system, sensor)
Outputs: Where data goes (user display, database, external API)
Valid ranges of inputs and outputs — Acceptable values
Units of measure — Units for numeric values
Data formats — Structure and encoding, e.g., JSON, CSV, UTF-8, etc.
Example
Interface: User Registration Form
Name: User Registration Input
Purpose: Collects new user information to create an account
Source: Web browser form submission
Valid ranges:
Email: Valid email format, max 255 characters
Password: 8-64 characters, must contain uppercase, lowercase, number, and special character
Age: 18-120
Units: N/A (text fields)
Data format: HTTP POST request with JSON body: {"email": "string", "password": "string", "age": integer}
Interface: User Registration and Login
Name: Login and Account Creation Page
Purpose: Allow users to create an account or log in to an existing Syllabify account
Source/destination: User data from a web browser form. Encrypted data stored in a database
Valid Ranges: 
Units: N/A
Data format: 

Interface: Syllabus Importation
Name: Syllabus Upload Page
Purpose: Users upload a syllabus document to be parsed by the system
Source/destination: 
Valid Ranges: 
Units: N/A
Data format: 
Interface: Course/Assignment/Schedule Creation
Name: 
Purpose: 
Source/destination: 
Valid Ranges: 
Units: 
Data format: 
Interface: Calendar Export
Name: 
Purpose: 
Source/destination: 
Valid Ranges: 
Units: 
Data format: iCalendar format

2.2 Functions
Define actions that must take place to accept and process inputs and generate outputs (ISO/IEC/IEEE 29148:2018). Include:
Validity checks on inputs
Sequence of operations in processing inputs
Responses to abnormal situations, including error handling and recovery
Relationship of outputs to inputs, including input/output sequences and formulas for conversion
Validity checks:
Check that user input follows app guidelines:
Valid email
Sufficiently strong/long password
Strings stored in database are not longer than allowed
Verify user permissions
Sequence of operations:
Sanitize user input
Check validity of inputs
Ensure user is permitted to make requested data alteration
Perform requested operation
Error Response:
Input/Output Relationship:

2.3 Usability Requirements
Define usability requirements and objectives, including measurable criteria for effectiveness, efficiency, and satisfaction, in specific contexts of use (ISO/IEC/IEEE 29148:2018).
Effectiveness:
Syllabus parser should not return false data, and instead clarify with the user when information is unclear in the syllabus
Efficiency: 


Satisfaction:
Users should find Syllabify more convenient than their current methods of checking schedules
Users should find Syllabify quicker that manually creating a study schedule themselves
2.4 Performance Requirements
Specify static and dynamic numerical requirements placed on the software or human interaction with it. Static numerical requirements may include the amount and type of information processed. Dynamic numerical requirements may include the amount of data processed within specific periods.
State performance requirements in measurable terms. Example: "95% of transactions shall be processed in less than 1 second" rather than "An operator shall not have to wait" (ISO/IEC/IEEE 29148:2018).
2.5 Software System Attributes
Specify required attributes such as reliability, security, privacy, maintainability, or portability (ISO/IEC/IEEE 29148:2018). Review comprehensive lists of software qualities (e.g., van Vliet 2008, Chapter 6). Select a relatively small number of the most important attributes. Explain why each is important and what steps you will take to achieve them. Attributes include constraints on static construction, such as testability, changeability, maintainability, and reusability (Faulk, 2013).
Modern considerations: Include security practices (e.g., input validation, authentication, data protection), accessibility requirements, and sustainability considerations where relevant.
3. References (at least one source per person)
List sources cited in this document. Provide inline citations where appropriate.
Cockburn, A. (2001). Writing Effective Use Cases. Addison-Wesley. https://kurzy.kpi.fei.tuke.sk/zsi/resources/CockburnBookDraft.pdf
IEEE Std 1362-1998 (R2007). IEEE Guide for Information Technology–System Definition–Concept of Operations (ConOps) Document. https://ieeexplore.ieee.org/document/761853
IEEE Std 830-1998. IEEE Recommended Practice for Software Requirements Specifications. https://ieeexplore.ieee.org/document/720574
ISO/IEC/IEEE Intl Std 29148:2018. Systems and software engineering — Life cycle processes — Requirements engineering. https://ieeexplore.ieee.org/document/8559686
Oracle. (2007). White Paper on "Getting Started With Use Case Modeling". https://www.oracle.com/technetwork/testcontent/gettingstartedwithusecasemodeling-133857.pdf
Sethi, Ravi. (2023). Software Engineering. Basic Principles and Best Practices. Cambridge Press.
4. Acknowledgments (ai?)
ChatGPT - Helped refine key points and writing style to be less informal and more professional.
