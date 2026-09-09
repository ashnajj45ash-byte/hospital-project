import os
import faiss
from sentence_transformers import SentenceTransformer


class HospitalRAG:
    def __init__(self, data_folder="hospital_data"):
        self.data_folder = data_folder

        # Model used to convert hospital text into embeddings
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        self.documents = []
        self.index = None

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

        # Convert text into embeddings
        embeddings = self.model.encode(
            self.documents
        )

        # Create FAISS search index
        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(
            dimension
        )

        self.index.add(embeddings)

    def search(self, question, top_k=3):
        """Find hospital information relevant to the question."""

        question_embedding = self.model.encode(
            [question]
        )

        distances, indices = self.index.search(
            question_embedding,
            top_k
        )

        results = []

        for index in indices[0]:
            if index < len(self.documents):
                results.append(self.documents[index])

        return results


rag = HospitalRAG()