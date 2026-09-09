import os
import re


class HospitalRAG:
    def __init__(self, data_folder="hospital_data"):
        self.data_folder = data_folder
        self.documents = []

        self.load_documents()

    def load_documents(self):
        """Load hospital information from .txt files."""

        for filename in os.listdir(self.data_folder):
            if filename.endswith(".txt"):

                filepath = os.path.join(
                    self.data_folder,
                    filename
                )

                with open(
                    filepath,
                    "r",
                    encoding="utf-8"
                ) as file:
                    text = file.read()

                # Split information into smaller sections
                chunks = [
                    chunk.strip()
                    for chunk in text.split("\n\n")
                    if chunk.strip()
                ]

                self.documents.extend(chunks)

        if not self.documents:
            raise RuntimeError(
                "No hospital documents found in hospital_data."
            )

    def search(self, question, top_k=3):
        """Find hospital information relevant to the question."""

        question_words = set(
            re.findall(r"\b[a-zA-Z0-9]+\b", question.lower())
        )

        # Words that don't help much with searching
        stop_words = {
            "what", "is", "are", "the", "a", "an",
            "where", "when", "how", "can", "i",
            "do", "does", "please", "tell", "me",
            "about", "of", "to", "for", "in",
            "on", "at", "and", "or", "my"
        }

        question_words -= stop_words

        scored_documents = []

        for document in self.documents:

            document_words = set(
                re.findall(
                    r"\b[a-zA-Z0-9]+\b",
                    document.lower()
                )
            )

            score = len(question_words & document_words)

            if score > 0:
                scored_documents.append(
                    (score, document)
                )

        # Highest matching documents first
        scored_documents.sort(
            key=lambda item: item[0],
            reverse=True
        )

        results = [
            document
            for score, document in scored_documents[:top_k]
        ]

        # If nothing matches, return the first few documents
        if not results:
            results = self.documents[:top_k]

        return results


rag = HospitalRAG()