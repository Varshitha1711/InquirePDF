## Acadbot: AI-Powered Syllabus-Based Study Assistant

Welcome to Acadbot, a centralized platform designed to provide syllabus-verified study materials and an AI chatbot trained on institution-approved resources. This system ensures students receive accurate answers aligned with their university or school syllabus, improving exam preparation and academic success.


### Features

- **Syllabus-Based Study Materials**: Get access to study materials and exam papers uploaded per syllabus schedule.
- **Institution-Specific AI Chatbot**: Ask academic queries and receive responses from a chatbot trained on prescribed textbooks and syllabus materials.
- **Smart Query Resolution**: Acadbot fetches answers from university-prescribed resources, ensuring alignment with evaluation criteria.
- **Efficient Search & Retrieval**: Uses AI-powered semantic search to provide relevant answers based on syllabus-based text embeddings.

### Prerequisites
Before setting up Acadbot, ensure you have the following installed:
-Python 3.x
-Flask (For building the web interface)
-LangChain (For AI-powered conversational retrieval)
-OpenAI GPT-3/GPT-4 (For chatbot responses)
-FAISS (For fast semantic search and vector database management)
-PyPDF2 (For extracting text from PDFs)

### Usage
#### 1. PDF Upload and Text Conversion
Users can upload PDFs containing syllabus-related study materials. The system extracts text and prepares it for AI-based retrieval.

#### 2. AI-Powered Query Resolution
The chatbot uses syllabus-specific embeddings to retrieve the most relevant responses for academic queries.

#### 3. Vector Store Generation
Text from uploaded materials is converted into vector embeddings using FAISS, ensuring fast and accurate information retrieval.

#### 4. Conversational Chatbot
Acadbot maintains chat history and provides consistent responses based on syllabus content.

#### 5. Information Retrieval
Users can search syllabus-specific study materials, find relevant topics, and get responses directly from prescribed textbooks.

### Future Scope

- **Expansion to More Universities & Boards**: Supporting more institutions with diverse syllabus content.
- **Integration with Learning Management Systems (LMS)**: Allowing seamless access within educational platforms.
- **Multi-Language Support**: Providing study materials and chatbot responses in different languages.
- **Advanced AI Models**: Implementing fine-tuned models for better accuracy and contextual understanding.

### Installation
1. Clone the repository to your local machine:
   ```
   git clone https://github.com/VamshidharReddy06/SyllabusBot-Assistant.git
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
