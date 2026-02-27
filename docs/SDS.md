Syllabify
Andrew Martin, Leon Wong, Kenny Nguyen, Saint George Aufranc
Software Design Specification Template
How to use this document: Keep the headings and document structure. Replace or modify the text within each section with the content described. Optionally add another level of structure in Section 2 to organize requirements around major user activities or system behaviors. The final SRS should be self-contained, clearly describing what the document is, who wrote each section, and when. Each section must specify who wrote it and when.
Delete all red text before submitting.
1. System Overview
Briefly describe the services provided by the software and how the system is organized, emphasizing software components and their interactions. The overview can discuss the user interface, but should not emphasize it.
2. Software Architecture
The term module refers to an independent component of a system (e.g., a "student records" module). The term component is used interchangeably.
2.1 Software Architecture
The software architecture description captures and communicates key design decisions about how the system is decomposed into components and the relationships among those components (Faulk, 2017). The architecture should describe:
The set of components must be presented in an easy-to-read list form and a diagram
The functionality each component provides
How modules interact with each other. Describe how components work together to achieve overall system functionality. Indicate this in the architectural diagram and give a brief description of each in the component list.
Describe modules at an abstraction level you would use to explain to a colleague how the system works. It should be abstract and static (e.g., "The client database holds all client information and interacts with the data-cleaning module to ensure no sensitive data gets released..."). It should not be a detailed textual description of the control flow.
The rationale for the architectural design in paragraph or list form. Explain how and why you decided this architecture was the best solution. See "Design Rationale" below.
Do not simplify your architecture just to reduce the number of modules. If your architecture has only one module, your project may be too small for an SDS, or there may be a design problem.
2.2 Naming Conventions
Use descriptive names for components. Each module should have a project-specific name. Do not use generic names such as "User Interface", "Model", "View", "Controller", "Database", "Back end", or "Front end". Instead, use names specific to functionality, such as "Instructor Interface", "Student Interface", "Roster", "Student Records", "Roster View", "Grade View".
Do not name modules "client" or "server". The roles of client and server are relative to a particular service. A component can be a server with respect to one service and a client with respect to another.
3. Software Modules
This section lists and describes the system's modules or components. Describe each module in a separate subsection.
<Module Name> (Include one subsection for each module.)
Each module's description must include:
The module's role and primary function
The interface to other modules
A static model
A dynamic model
A design rationale
3.1 Module Role and Primary Function
Each module must be described abstractly in terms of its function or role in the system, followed by its data structures and functionality. Lists and diagrams provide more readable and searchable formats than paragraphs.
Use indented, numbered lists for requirements:
General Requirement
Specific Requirement
Requirement Detail
This numbering scheme permits reference to other parts of the document, e.g., SRS 1.1.1.
3.2 Interface Specification
A software interface specification describes precisely how one part of a program interacts with another. A software interface is not the user interface; it is a description of services, such as public methods in a class. Describe the software interface each module makes available to other internal and external software components. This helps explain how components interact, which services each module provides, how to access them, and how to implement each module.
Find the right abstraction for each interface specification. Describe services that modules provide, but not their implementation. An interface that reveals too much information is over-specified and limits implementation freedom.
Modern considerations: For API-based designs, include REST/GraphQL endpoint specifications, authentication mechanisms, rate limiting, and versioning strategies.
3.3 Static and Dynamic Models
Describe software modules with static or dynamic models—preferably both. Each diagram should use a specific design language (UML is recommended), emphasizing static or dynamic representation, and should not typically mix the two. For example, class diagrams are primarily static, though they hint at dynamic activities in method names. Sequence diagrams emphasize activities over time and list interacting entities (classes). However, you do not typically see dynamic activity indicated on an association between two classes in a class diagram.
Every figure must include a caption immediately below it. Each caption starts with "Figure <x>." and is referenced in the body text as "Figure <x>." The caption briefly describes the figure (e.g., "Figure 3. A sequence diagram showing the 'Feed a child' use-case.").
Diagrams can be hand-drawn and scanned, but scan them rather than photograph them to keep file sizes down. Do not fill an SDS with large (>1MB each) high-resolution photos of hand-drawn diagrams.
3.4 Design Rationale
There will be a reason to design each module (and the architecture) as it is. "Design rationale may take the form of commentary, made throughout the decision process and associated with collections of design elements. Design rationale may include design issues raised and addressed in response to design concerns, design options considered, trade-offs evaluated, decisions made, criteria used to guide design decisions, and arguments and justifications made to reach decisions" (IEEE Std 1016-2009). Your design should clearly separate responsibilities for each module. One design rationale required by IEEE Std 1016-2009 is "a description of why the element exists, ... to provide the rationale for the creation of the element."
4. Alternative Designs
Your SDS should include alternate designs considered for the architecture and each system or subsystem. These designs may result from evaluating multiple alternatives considered during the project or from your design evolving throughout the project.
Alternative design ideas and diagrams can be placed in a separate section titled "Alternative Designs" or "Earlier Designs," or immediately after each current design and labeled as an alternative or earlier design.
If you do not consider alternatives, you are not doing design. If you do not document the other options you considered, your design practice is weak. If there were no alternatives, there would be no design work.
5. Database Design
Design the database that the system will use to store information. Specify the design using an ER diagram. The database must be at least in third normal form (see https://en.wikipedia.org/wiki/Database_normalization).
Modern considerations: If you are using NoSQL databases, document the data model and the rationale. Include considerations for data migration, backup strategies, and scalability.
6. References
An SDS should reference all sources it draws from. This section may not be necessary if sufficient citations are provided inline.
IEEE Std 1016-2009. IEEE Standard for Information Technology—Systems Design— Software Design Descriptions. https://ieeexplore.ieee.org/document/5167255
Parnas, D. L. (1972). On the criteria to be used in decomposing systems into modules. Commun. ACM, 15(12), 1053-1058.
Class Diagram. In Wikipedia. https://en.wikipedia.org/wiki/Class_diagram
Sequence Diagram. In Wikipedia. https://en.wikipedia.org/wiki/Sequence_diagram
7. Acknowledgments
List all sources used to create this document and any support received from anyone not on your team.
