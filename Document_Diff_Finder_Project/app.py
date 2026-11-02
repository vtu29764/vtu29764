import difflib
import html
import random
import re
from io import BytesIO

import streamlit as st
import pymupdf
from docx import Document


# =========================================================
# PAGE CONFIGURATION AND STYLING
# =========================================================
st.set_page_config(
    page_title="Document Diff Finder + Study Assistant",
    page_icon="📚",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; max-width: 1200px;}
    .app-subtitle {color: #64748b; text-align: center; margin-bottom: 1.4rem;}
    .diff-box {
        background: #ffffff; color: #1f2937; border: 1px solid #d1d5db;
        border-radius: 10px; padding: 14px; max-height: 600px;
        overflow-y: auto; overflow-wrap: anywhere; line-height: 1.75;
    }
    .diff-line {padding: 7px 10px; margin: 5px 0; border-radius: 4px; white-space: pre-wrap; color: #111827; background: #ffffff; border-bottom: 1px solid #eeeeee;}
    .same {background: #fff; color: #111827; border-bottom: 1px solid #eeeeee;}
    .removed {background: #ffffff; color: #111827; border-left: 3px solid #e5a3a3;}
    .added {background: #ffffff; color: #111827; border-left: 3px solid #a7d8b5;}
    .small-note {font-size: 0.9rem; color: #64748b;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📚 Document Diff Finder")
st.markdown(
    '<p class="app-subtitle">Compare files, understand changes, and practise for exams.</p>',
    unsafe_allow_html=True,
)


# =========================================================
# DOCUMENT TEXT EXTRACTION
# =========================================================
def extract_text(uploaded_file):
    """Extract readable text from PDF, DOCX, or TXT uploads."""
    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    if name.endswith(".pdf"):
        parts = []
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            for page in pdf:
                parts.append(page.get_text("text"))
        return "\n".join(parts)

    if name.endswith(".docx"):
        doc = Document(BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.replace("\n", " ").strip() for cell in row.cells)
                if row_text.strip(" |"):
                    parts.append(row_text)
        return "\n".join(parts)

    if name.endswith(".txt"):
        return data.decode("utf-8-sig", errors="replace")

    raise ValueError("Unsupported file. Please upload PDF, DOCX, or TXT.")


def clean_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Keep paragraph breaks, remove trailing spaces and excessive blank lines.
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def prepare_readable_text(text):
    """Normalize common Markdown and PDF line-wrap artifacts for readable study output."""
    text = clean_text(text)
    # Remove Markdown heading markers and common inline formatting markers, not the words.
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?<!\*)\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(.*?)\*", r"\1", text)
    text = re.sub(r"(?<!_)__(.*?)__(?!_)", r"\1", text)
    text = re.sub(r"(?m)^\s*[-*•]\s+", "• ", text)
    # Join single line breaks within a paragraph (common in extracted PDFs), preserve blank lines.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# =========================================================
# DOCUMENT COMPARISON
# =========================================================
def compare_documents(old_text, new_text):
    """
    Compare normalized paragraphs. Keep document text black and unhighlighted.
    Changes are shown as plain-text entries under Added / Removed labels.
    """
    def paragraphs(value):
        value = prepare_readable_text(value)
        return [p.strip() for p in value.split("\n\n") if p.strip()]

    old_paras = paragraphs(old_text)
    new_paras = paragraphs(new_text)

    matcher = difflib.SequenceMatcher(None, old_paras, new_paras, autojunk=False)
    rendered = []
    added_count = 0
    removed_count = 0
    unchanged_count = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for paragraph in old_paras[i1:i2]:
                rendered.append(
                    '<div class="diff-line same">' + html.escape(paragraph) + '</div>'
                )
                unchanged_count += 1
        elif tag == "delete":
            for paragraph in old_paras[i1:i2]:
                rendered.append(
                    '<div class="diff-line removed"><strong>Removed:</strong> '
                    + html.escape(paragraph) + '</div>'
                )
                removed_count += len(paragraph.split())
        elif tag == "insert":
            for paragraph in new_paras[j1:j2]:
                rendered.append(
                    '<div class="diff-line added"><strong>Added:</strong> '
                    + html.escape(paragraph) + '</div>'
                )
                added_count += len(paragraph.split())
        else:
            # For changed paragraphs, show old and new versions as plain black text.
            old_block = old_paras[i1:i2]
            new_block = new_paras[j1:j2]
            old_words = " ".join(old_block).split()
            new_words = " ".join(new_block).split()
            word_matcher = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False)
            removed_words = []
            added_words = []
            for wtag, a1, a2, b1, b2 in word_matcher.get_opcodes():
                if wtag in ("delete", "replace"):
                    removed_words.extend(old_words[a1:a2])
                if wtag in ("insert", "replace"):
                    added_words.extend(new_words[b1:b2])

            if old_block:
                old_text_block = " ".join(old_block)
                rendered.append(
                    '<div class="diff-line removed"><strong>Removed version:</strong> '
                    + html.escape(old_text_block) + '</div>'
                )
                removed_count += len(removed_words)
            if new_block:
                new_text_block = " ".join(new_block)
                rendered.append(
                    '<div class="diff-line added"><strong>Added version:</strong> '
                    + html.escape(new_text_block) + '</div>'
                )
                added_count += len(added_words)

    similarity = difflib.SequenceMatcher(
        None, clean_text(old_text), clean_text(new_text), autojunk=False
    ).ratio() * 100

    return "\n".join(rendered), round(similarity, 2), added_count, removed_count, unchanged_count


# =========================================================
# STUDY NOTES: HEURISTIC QUESTION GENERATION
# This works offline. It is a basic automatic question generator,
# not a substitute for a language model or teacher review.
# =========================================================
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be", "been",
    "being", "to", "of", "in", "on", "for", "from", "by", "with", "as", "at", "it",
    "this", "that", "these", "those", "can", "could", "should", "would", "will",
    "may", "might", "must", "do", "does", "did", "have", "has", "had", "not", "than",
    "then", "which", "what", "when", "where", "who", "why", "how", "their", "there",
    "they", "them", "its", "into", "also", "such", "each", "other", "more", "most",
    "many", "some", "any", "all", "both", "using", "use", "used", "we", "you", "your",
    "our", "he", "she", "his", "her", "i", "me", "my", "if", "about", "through",
    "between", "within", "after", "before", "because", "while", "per", "etc",
}


def split_sentences(text):
    # Preserve useful sentences; ignore very short fragments.
    raw = re.split(r"(?<=[.!?])\s+|\n+", text)
    sentences = []
    for item in raw:
        item = re.sub(r"\s+", " ", item).strip(" \t-•")
        if len(item.split()) >= 5:
            sentences.append(item)
    return sentences


def important_terms(text, limit=30):
    words = re.findall(r"\b[A-Za-z][A-Za-z0-9'-]{3,}\b", text)
    counts = {}
    for word in words:
        key = word.lower()
        if key not in STOPWORDS and not key.isdigit():
            counts[key] = counts.get(key, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]]


def make_study_questions(text, max_questions=10):
    """
    Create simple fill-the-key-term MCQs from uploaded study material.
    Questions are generated only where a plausible target term is found.
    """
    sentences = split_sentences(text)
    terms = important_terms(text)
    questions = []
    used_terms = set()

    # Prefer a term that appears in a sentence and can be blanked.
    for sentence in sentences:
        if len(questions) >= max_questions:
            break

        lower_sentence = sentence.lower()
        candidates = [
            term for term in terms
            if term not in used_terms and re.search(r"\b" + re.escape(term) + r"\b", lower_sentence)
        ]
        if not candidates:
            continue

        # Prefer longer, distinctive terms for a clearer question.
        answer = sorted(candidates, key=lambda t: (-len(t), t))[0]
        pattern = re.compile(r"\b" + re.escape(answer) + r"\b", re.IGNORECASE)
        question_text = pattern.sub("________", sentence, count=1)

        # Need enough distinct distractors from the same document.
        distractors = [
            term for term in terms
            if term != answer and term.lower() not in used_terms
        ]
        if len(distractors) < 3:
            distractors = [term for term in terms if term != answer]
        distractors = distractors[:3]
        if len(distractors) < 3:
            continue

        options = distractors + [answer]
        random.Random(f"{answer}-{sentence}").shuffle(options)
        questions.append({
            "question": f"Choose the term that best completes this statement:\n\n{question_text}",
            "options": options,
            "answer": answer,
            "source": sentence,
        })
        used_terms.add(answer.lower())

    return questions


def make_important_points(text, limit=8):
    sentences = split_sentences(prepare_readable_text(text))
    if not sentences:
        return []
    terms = important_terms(text, limit=25)
    ranked = []
    for idx, sentence in enumerate(sentences):
        words = re.findall(r"\b[A-Za-z][A-Za-z0-9'-]{3,}\b", sentence.lower())
        score = sum(1 for word in words if word in terms)
        # Slight preference for earlier sentences when scores are tied.
        ranked.append((score, -idx, sentence))
    ranked.sort(reverse=True)
    return [entry[2] for entry in ranked[:limit]]


def make_question_bank(text, max_questions=10):
    """Create study questions from the uploaded material's key sentences and terms."""
    sentences = split_sentences(prepare_readable_text(text))
    terms = important_terms(text, limit=40)
    result = []
    seen = set()
    for sentence in sentences:
        if len(result) >= max_questions:
            break
        matching = [term for term in terms if re.search(r"\b" + re.escape(term) + r"\b", sentence, re.I)]
        if not matching:
            continue
        term = sorted(matching, key=lambda x: (-len(x), x))[0]
        question = f"Explain the meaning, function, or importance of {term.title()} based on the uploaded material."
        if question.lower() not in seen:
            result.append(question)
            seen.add(question.lower())
    # If terms did not produce enough questions, use sentence-based revision prompts.
    for sentence in sentences:
        if len(result) >= max_questions:
            break
        question = f"Explain the following concept in your own words: {sentence}"
        if question.lower() not in seen:
            result.append(question)
            seen.add(question.lower())
    return result


def explain_comparison(added, removed, similarity):
    """Plain-language interpretation of comparison metrics."""
    if similarity >= 90:
        level = "The documents are very similar. Only a small amount of text appears to have changed."
    elif similarity >= 60:
        level = "The documents are partly similar. Review the added and removed sections carefully."
    else:
        level = "The documents differ substantially. They may cover different versions or different content."
    details = [level]
    if added == 0 and removed == 0:
        details.append("No added or removed words were detected by the comparison method.")
    else:
        if added:
            details.append(f"Approximately {added} word(s) were added in the updated document.")
        if removed:
            details.append(f"Approximately {removed} word(s) were removed from the original document.")
    details.append("Use this comparison to review edits, updated facts, missing sections, or changes between study-note versions. Similarity is a text-based estimate, not a judgment of correctness.")
    return details


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.header("How to use")
    st.markdown(
        """
        1. **Compare Documents:** Upload an old and new file.
        2. **Study Assistant:** Upload study material.
        3. Read important points and questions.
        4. Take the 4-option quiz.
        5. Submit to see your score and corrections.
        """
    )
    st.caption("Supported formats: PDF, DOCX, TXT")


# =========================================================
# TABS
# =========================================================
compare_tab, study_tab = st.tabs(["🔎 Compare Documents", "🎓 Study Assistant & Quiz"])


# =========================================================
# TAB 1: COMPARE DOCUMENTS
# =========================================================
with compare_tab:
    st.subheader("Compare an original file with an updated file")
    st.caption("Upload TWO files here: the original/older version on the left and the newer/updated version on the right. The result appears below after you click Compare uploaded documents.")
    c1, c2 = st.columns(2)

    with c1:
        old_file = st.file_uploader(
            "Upload original document",
            type=["pdf", "docx", "txt"],
            key="compare_old",
        )
    with c2:
        new_file = st.file_uploader(
            "Upload updated document",
            type=["pdf", "docx", "txt"],
            key="compare_new",
        )

    if st.button("Compare uploaded documents", type="primary", key="run_compare", use_container_width=True):
        if not old_file or not new_file:
            st.warning("Please upload both documents first.")
        else:
            try:
                old_text = extract_text(old_file)
                new_text = extract_text(new_file)
                if not old_text.strip() or not new_text.strip():
                    st.error(
                        "No readable text was extracted from one or both files. "
                        "Scanned PDFs need OCR before they can be compared."
                    )
                else:
                    diff_html, similarity, added, removed, unchanged = compare_documents(old_text, new_text)
                    st.session_state["comparison_result"] = {
                        "html": diff_html,
                        "similarity": similarity,
                        "added": added,
                        "removed": removed,
                        "unchanged": unchanged,
                        "old_name": old_file.name,
                        "new_name": new_file.name,
                    }
            except Exception as exc:
                st.error(f"Could not read or compare these files: {exc}")

    result = st.session_state.get("comparison_result")
    if result:
        st.success("Comparison is ready.")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Text similarity", f'{result["similarity"]}%')
        m2.metric("Added words (approx.)", result["added"])
        m3.metric("Removed words (approx.)", result["removed"])
        m4.metric("Unchanged lines", result["unchanged"])

        st.subheader("What do these differences mean?")
        for explanation in explain_comparison(result["added"], result["removed"], result["similarity"]):
            st.write("• " + explanation)
        st.caption("All comparison text is black and is not highlighted. A thin side line labels removed or added paragraphs. Word counts are approximate.")
        st.markdown(
            f'<div class="diff-box">{result["html"]}</div>',
            unsafe_allow_html=True,
        )

        report = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Document Diff Report</title>
<style>
body{{font-family:Arial,sans-serif;line-height:1.7;margin:30px;color:#1f2937}}
.diff-box{{border:1px solid #ddd;border-radius:8px;padding:15px}}
.diff-line{{padding:5px;margin:3px 0;white-space:pre-wrap;overflow-wrap:anywhere}}
.same{{background:#fff;color:#111827;border-bottom:1px solid #eee}}
.removed{{background:#fff;color:#111827;border-left:3px solid #e5a3a3}}
.added{{background:#fff;color:#111827;border-left:3px solid #a7d8b5}}
</style></head><body>
<h1>Document Diff Finder Report</h1>
<p><b>Original:</b> {html.escape(result["old_name"])}</p>
<p><b>Updated:</b> {html.escape(result["new_name"])}</p>
<p><b>Similarity:</b> {result["similarity"]}%</p>
<p><b>Added words (approx.):</b> {result["added"]} | <b>Removed words (approx.):</b> {result["removed"]}</p>
<div class="diff-box">{result["html"]}</div></body></html>"""

        st.download_button(
            "⬇️ Download comparison report (HTML)",
            data=report,
            file_name="document_diff_report.html",
            mime="text/html",
        )


# =========================================================
# TAB 2: STUDY ASSISTANT AND EXAM QUIZ
# =========================================================
with study_tab:
    st.subheader("Upload study material to prepare notes and a practice quiz")
    st.info(
        "Upload one study file, then click Analyze study material. The app cleans common Markdown headings, "
        "extracts important points, suggests revision questions, and creates a 4-option practice exam. "
        "Questions are generated automatically from the file, so review them against your syllabus."
    )

    study_file = st.file_uploader(
        "Upload your study material (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        key="study_upload",
    )

    if study_file:
        try:
            study_text = prepare_readable_text(extract_text(study_file))
            if not study_text:
                st.error("No readable text found. A scanned PDF may need OCR.")
            else:
                st.success(f"Read {len(study_text.split())} words from {study_file.name}.")
                with st.expander("Preview extracted text"):
                    st.text(study_text[:5000] + ("\n\n[Preview shortened]" if len(study_text) > 5000 else ""))

                if st.button("Analyze study material", type="primary", key="analyze_study"):
                    st.session_state.pop("quiz_result", None)
                    st.session_state["study_analysis"] = {
                        "name": study_file.name,
                        "text": study_text,
                        "points": make_important_points(study_text),
                        "questions": make_question_bank(study_text, max_questions=10),
                        "quiz": make_study_questions(study_text, max_questions=10),
                    }

        except Exception as exc:
            st.error(f"Could not analyze this file: {exc}")

    analysis = st.session_state.get("study_analysis")
    if analysis:
        st.divider()
        st.subheader("📌 Important points")
        if analysis["points"]:
            for idx, point in enumerate(analysis["points"], start=1):
                st.markdown(f"{idx}. {point}")
        else:
            st.warning("Not enough complete sentences were found to extract important points.")

        st.subheader("📝 Suggested important questions")
        if analysis["questions"]:
            for idx, question in enumerate(analysis["questions"], start=1):
                st.markdown(f"{idx}. {question}")
        else:
            st.warning("Could not automatically make questions from this text.")

        st.caption(
            "The questions above are automatically suggested from frequent terms in the document. "
            "They are not guaranteed to be the exact questions your lecturer will ask."
        )

        st.divider()
        st.subheader("🧪 Practice exam")
        quiz = analysis["quiz"]

        if not quiz:
            st.warning(
                "This file did not provide enough suitable text to create a 4-option quiz. "
                "Try a text-based study PDF or DOCX with complete sentences."
            )
        else:
            st.write(f"Number of questions: **{len(quiz)}**. Select one option for each question, then click Submit exam. Your score and correct answers appear only after submission.")

            # Render the quiz as a form so the user can answer without seeing correctness first.
            with st.form("practice_exam_form"):
                selected_answers = {}
                for idx, question in enumerate(quiz, start=1):
                    st.markdown(f"**Q{idx}. {question['question']}**")
                    labels = [str(option) for option in question["options"]]
                    selected = st.radio(
                        "Choose one answer:",
                        options=labels,
                        index=None,
                        key=f"quiz_answer_{idx}_{analysis['name']}",
                        label_visibility="collapsed",
                    )
                    selected_answers[idx - 1] = selected
                    st.markdown("---")

                submitted = st.form_submit_button("Submit exam", type="primary", use_container_width=True)

            if submitted:
                correct = 0
                review = []
                for idx, question in enumerate(quiz):
                    selected = selected_answers.get(idx)
                    answer = question["answer"]
                    is_correct = selected is not None and selected.lower() == answer.lower()
                    if is_correct:
                        correct += 1
                    review.append({
                        "number": idx + 1,
                        "question": question["question"],
                        "selected": selected or "Not answered",
                        "answer": answer,
                        "correct": is_correct,
                        "source": question["source"],
                    })

                st.session_state["quiz_result"] = {
                    "correct": correct,
                    "total": len(quiz),
                    "review": review,
                    "study_name": analysis["name"],
                }

    quiz_result = st.session_state.get("quiz_result")
    if quiz_result and analysis and quiz_result["study_name"] == analysis["name"]:
        st.divider()
        st.subheader("📊 Exam result")
        score = quiz_result["correct"]
        total = quiz_result["total"]
        percentage = round(score / total * 100, 2) if total else 0
        st.metric("Your score", f"{score} / {total}", f"{percentage}%")
        if percentage >= 80:
            st.success("Great work! Review the explanations and practise again.")
        elif percentage >= 50:
            st.info("Good start. Review the incorrect answers and try again.")
        else:
            st.warning("Read the study material again, then retry the quiz.")

        st.subheader("Answer review")
        for item in quiz_result["review"]:
            if item["correct"]:
                st.success(f'Q{item["number"]}: Correct')
                st.write(f'Your answer: {item["selected"]}')
            else:
                st.error(f'Q{item["number"]}: Wrong or unanswered')
                st.write(f'Your answer: {item["selected"]}')
                st.write(f'Correct answer: {item["answer"]}')
            st.caption(f'From your uploaded material: {item["source"]}')
            st.markdown("---")

        if st.button("Retake exam", key="retake_exam"):
            st.session_state.pop("quiz_result", None)
            st.rerun()

st.caption("Document Diff Finder · Python + Streamlit")
