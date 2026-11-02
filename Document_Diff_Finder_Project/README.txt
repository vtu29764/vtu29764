DOCUMENT DIFF FINDER + STUDY ASSISTANT

FEATURES
1. Compare an original file with an updated file (PDF, DOCX, or TXT).
2. View text similarity, approximate added/removed words, and unchanged paragraphs.
3. See a plain-language explanation of what the differences may mean.
4. Text remains black and is not highlighted; only a subtle side border labels added/removed paragraphs.
5. Upload study material (PDF, DOCX, TXT) to extract important points and revision questions.
6. Take a 10-question, four-option practice quiz.
7. After submission, view the score, correct/wrong status, selected answer, correct answer, and source sentence.

RUN ON WINDOWS
1. Extract this ZIP into a folder.
2. Open the folder in VS Code.
3. Open Terminal > New Terminal.
4. (Recommended) Create a virtual environment:
   python -m venv .venv
5. Activate it in PowerShell:
   .\.venv\Scripts\Activate.ps1
6. Install packages:
   python -m pip install -r requirements.txt
7. Start the app:
   python -m streamlit run app.py
8. Open the local address printed in the terminal.

HOW TO USE COMPARISON
- In the Compare Documents tab, upload the OLD/original file on the left.
- Upload the NEW/updated file on the right.
- Click Compare uploaded documents.
- Scroll down to see metrics, difference explanation, and the detailed comparison.

HOW TO USE STUDY ASSISTANT
- Open Study Assistant & Quiz.
- Upload one study material file.
- Click Analyze study material.
- Review important points and suggested questions.
- Answer the 4-option quiz and click Submit exam.
- The result shows correct/wrong answers and the correct answer for each wrong or unanswered question.

SUPPORTED FILES
PDF, DOCX, TXT. Scanned/image-only PDFs may not contain extractable text and may require OCR first.

NOTE
The quiz generator is an offline, rule-based helper. It does not guarantee exam questions and should be checked against your class notes/syllabus.
