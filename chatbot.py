import os
from groq import Groq
from dotenv import load_dotenv
from rag import rag

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found. Create a .env file with GROQ_API_KEY=your_key_here"
    )

client = Groq(api_key=GROQ_API_KEY)


SYSTEM_PROMPT = (
    "You are MediTrust AI, a helpful hospital information assistant. "
    "Answer questions about hospital services, departments, appointments, "
    "billing, and general facility info as helpfully as you can. "
    "Never provide medical diagnoses, prescriptions, or treatment advice — "
    "for medical concerns, direct the user to a doctor or emergency services. "
    "Keep answers concise and friendly."
)


class Chatbot:

    def ask(self, question: str, history=None):

        # Search the hospital knowledge base using RAG
        retrieved_documents = rag.search(question)

        # Combine retrieved hospital information
        context = "\n\n".join(retrieved_documents)

        # Give the retrieved information to the LLM
        system_prompt = SYSTEM_PROMPT + f"""

Use the following hospital information to answer the user's question:

HOSPITAL INFORMATION:
{context}

Important:
- Use the hospital information when relevant.
- Do not invent hospital information.
- If the information is not available, say that you do not have that information.
"""

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        if history:
            messages.extend(history[-6:])

        messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=500,
        )

        answer = response.choices[0].message.content

        return {"answer": answer}


rag_chatbot = Chatbot()


if __name__ == "__main__":
    print("MediTrust AI chatbot — type 'exit' to quit")

    while True:
        q = input("\nYou: ")

        if q.lower() in ("exit", "quit"):
            break

        result = rag_chatbot.ask(q)

        print(f"\nBot: {result['answer']}")