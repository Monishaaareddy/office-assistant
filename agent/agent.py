import os
import re

from google import genai
from rag.retriever import retrieve

from agent.memory import (
    ShortTermMemory,
    save_memory,
    load_memories
)

from memory.conversation_history import get_history

from tools import (
    get_employee_info,
    get_leave_balance,
    apply_leave,
    get_expense_status,
    get_it_assets,
    get_employee_office,
    get_manager_info,
    submit_expense,
)


def search_policy(query):
    """
    Search company policy documents using the RAG system.
    Returns {"answer": "...", "sources": [...]}.
    """
    results = retrieve(query, top_k=3)

    if not results:
        return {"answer": "No relevant policy information was found.", "sources": []}

    response_parts = []
    sources = []
    for result in results:
        response_parts.append(
            f"Source: {result['source']}\n"
            f"Page: {result['page']}\n"
            f"{result['text']}"
        )
        citation = f"{result['source']}, Page {result['page']}"
        if citation not in sources:
            sources.append(citation)

    return {
        "answer": "\n\n-----------------------------\n\n".join(response_parts),
        "sources": sources,
    }


# Gemini client
client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


class OfficeAssistant:

    def __init__(self):
        self.short_term_memory = ShortTermMemory()
        self.long_term_memory = load_memories()

    def decide_tools(self, question):
        """
        Decide which tool(s) should handle the question.
        Returns a LIST — a single question can need more than one tool
        (e.g. "what's the leave policy AND how many leaves do I have left").
        """

        q = question.lower().strip()
        employee_id = self.extract_employee_id(question)
        matched = []

        # Leave: action vs. balance query — mutually exclusive with each other
        leave_action = "leave" in q and any(
            v in q for v in ["apply", "book", "take", "request", "need"]
        )
        if leave_action:
            matched.append("apply_leave")
        elif any(p in q for p in [
            "leave balance", "casual leave", "earned leave", "sick leave",
            "how much leave", "remaining leave", "leaves remaining",
            "leave remaining", "how many leaves"
        ]):
            matched.append("leave")

        # Expense: action vs. status query — mutually exclusive with each other
        expense_action = any(p in q for p in [
            "submit an expense", "submit expense", "file an expense",
            "raise an expense", "claim an expense", "expense claim"
        ])
        if expense_action:
            matched.append("submit_expense")
        elif any(p in q for p in [
            "expense status", "expense claim status", "expense claims",
            "pending expense", "reimbursement status", "my reimbursement", "my expense"
        ]):
            matched.append("expense_status")

        # Independent categories — any of these can combine with anything else
        if "manager" in q or "reporting manager" in q:
            matched.append("manager")

        if any(p in q for p in [
            "laptop", "monitor", "keyboard", "mouse", "it asset", "it assets",
            "equipment issued", "asset issued", "my asset", "my assets",
            "serial number", "device", "devices"
        ]):
            matched.append("it_asset")

        if any(p in q for p in [
            "office location", "which office", "office address",
            "where is my office", "my office"
        ]):
            matched.append("office_location")

        if any(p in q for p in [
            "policy", "travel policy", "travel", "hotel policy", "hotel",
            "reimbursement policy", "reimbursement", "work from home",
            "wfh policy", "benefits", "security policy", "security",
            "expense policy", "leave policy", "it policy", "onboarding",
            "office guidelines"
        ]):
            matched.append("policy")

        if any(p in q for p in [
            "summary of my recent questions", "summarize my conversation",
            "summarize my questions", "recent questions", "conversation topics",
            "what have i asked", "recap my questions", "chat history summary",
            "summary of my questions", "summarize my recent"
        ]):
            matched.append("history_summary")

        # Employee info — only added if nothing more specific already matched,
        # unless the question explicitly asks for employee details
        if employee_id:
            if any(p in q for p in [
                "information", "details", "detail", "profile", "record",
                "employee info", "employee information", "employee details",
                "employee record", "about", "tell me about"
            ]):
                matched.append("employee")
            elif not matched:
                matched.append("employee")
        elif any(p in q for p in [
            "employee information", "employee details", "employee profile",
            "department", "designation", "joining date", "who is"
        ]):
            matched.append("employee")

        if not matched:
            matched.append("general")

        return matched

    def run_tools(self, tool_names, question):
        """
        Execute every matched tool and return a dict of
        {tool_name: result} so multiple results can be combined.
        """

        employee_id = self.get_employee_id_from_context(question)
        results = {}

        for tool_name in tool_names:

            if tool_name == "policy":
                results["policy"] = search_policy(question)

            elif tool_name == "employee":
                results["employee"] = (
                    get_employee_info(employee_id) if employee_id
                    else "Please provide the employee ID."
                )

            elif tool_name == "leave":
                results["leave"] = (
                    get_leave_balance(employee_id) if employee_id
                    else "Please provide the employee ID."
                )

            elif tool_name == "expense_status":
                results["expense_status"] = (
                    get_expense_status(employee_id) if employee_id
                    else "Please provide the employee ID."
                )

            elif tool_name == "it_asset":
                results["it_asset"] = (
                    get_it_assets(employee_id) if employee_id
                    else "Please provide the employee ID."
                )

            elif tool_name == "office_location":
                results["office_location"] = (
                    get_employee_office(employee_id) if employee_id
                    else "Please provide the employee ID."
                )

            elif tool_name == "manager":
                results["manager"] = (
                    get_manager_info(employee_id) if employee_id
                    else "Please provide the employee ID."
                )

            elif tool_name == "apply_leave":
                if not employee_id:
                    results["apply_leave"] = "Please provide your employee ID to apply for leave."
                else:
                    leave_type = self.extract_leave_type(question)
                    days = self.extract_days(question)
                    if not leave_type:
                        results["apply_leave"] = "Please specify the leave type: casual, earned, or sick."
                    elif not days:
                        results["apply_leave"] = "Please specify how many days you'd like to apply for."
                    else:
                        results["apply_leave"] = apply_leave(employee_id, leave_type, days)

            elif tool_name == "submit_expense":
                if not employee_id:
                    results["submit_expense"] = "Please provide your employee ID to submit an expense."
                else:
                    category = self.extract_expense_category(question)
                    amount = self.extract_amount(question)
                    if not category:
                        results["submit_expense"] = "Please specify the expense category (e.g. Travel, Food, Accommodation)."
                    elif not amount:
                        results["submit_expense"] = "Please specify the expense amount."
                    else:
                        results["submit_expense"] = submit_expense(employee_id, category, amount)

            elif tool_name == "history_summary":
                history = get_history()
                if not history:
                    results["history_summary"] = "No conversation history found yet."
                else:
                    recent = history[:10]
                    lines = [f"- {q}" for _, q, a, _ in reversed(recent)]
                    results["history_summary"] = (
                        "Recent questions asked, oldest to newest:\n" + "\n".join(lines)
                    )

            # "general" contributes nothing — Gemini answers without tool data

        return results

    def extract_employee_id(self, question):
        match = re.search(r"\bEMP\d+\b", question.upper())
        return match.group() if match else None

    def get_employee_id_from_context(self, question):
        employee_id = self.extract_employee_id(question)
        if employee_id:
            return employee_id

        messages = self.short_term_memory.get_messages()
        for message in reversed(messages):
            employee_id = self.extract_employee_id(message["content"])
            if employee_id:
                return employee_id

        return None

    def extract_leave_type(self, question):
        q = question.lower()
        if "casual" in q:
            return "casual"
        if "earned" in q:
            return "earned"
        if "sick" in q:
            return "sick"
        return None

    def extract_days(self, question):
        match = re.search(r"(\d+)\s*day", question.lower())
        return int(match.group(1)) if match else None

    def extract_amount(self, question):
        match = re.search(r"(\d+(?:\.\d+)?)", question.replace(",", ""))
        return float(match.group(1)) if match else None

    def extract_expense_category(self, question):
        q = question.lower()
        category_map = {
            "travel": "Travel", "food": "Food", "meal": "Food",
            "hotel": "Accommodation", "accommodation": "Accommodation",
            "internet": "Internet Reimbursement", "supplies": "Office Supplies",
            "training": "Training/Certification", "certification": "Training/Certification",
            "mobile": "Mobile Bill", "cab": "Cab/Local Conveyance",
            "conveyance": "Cab/Local Conveyance",
        }
        for keyword, category in category_map.items():
            if keyword in q:
                return category
        return None

    def detect_memory(self, question):
        question_lower = question.lower()
        memory_phrases = ["remember that", "remember this", "keep in mind", "save this", "note that"]

        for phrase in memory_phrases:
            if phrase in question_lower:
                start_index = question_lower.find(phrase)
                information = question[start_index + len(phrase):].strip()
                if information:
                    memory_item = {"type": "user_preference", "information": information}
                    save_memory(memory_item)
                    self.long_term_memory.append(memory_item)
                    return memory_item

        return None

    def build_context(self):
        messages = self.short_term_memory.get_messages()
        if not messages:
            return ""
        context = ""
        for message in messages:
            context += f"{message['role']}: {message['content']}\n"
        return context

    def build_memory_context(self):
        if not self.long_term_memory:
            return ""
        context = ""
        for memory in self.long_term_memory:
            context += (
                f"Type: {memory.get('type', 'unknown')}\n"
                f"Information: {memory.get('information', '')}\n"
            )
        return context

    def answer(self, question):
        """
        Main agent workflow — now multi-intent aware.
        """

        self.short_term_memory.add_message("user", question)

        memory_item = self.detect_memory(question)
        memory_context = self.build_memory_context()

        tool_names = self.decide_tools(question)
        tool_results = self.run_tools(tool_names, question)

        conversation = self.build_context()

        # Combine every tool's result into one labeled block for the prompt,
        # and separately collect policy citations.
        tool_result_sections = []
        policy_sources = []

        for name, result in tool_results.items():
            if name == "policy" and isinstance(result, dict):
                tool_result_sections.append(f"[{name}]\n{result.get('answer', '')}")
                policy_sources = result.get("sources", [])
            else:
                tool_result_sections.append(f"[{name}]\n{result}")

        tool_result_text = "\n\n".join(tool_result_sections) if tool_result_sections else None

        if tool_result_text:
            prompt = f"""
You are an intelligent Office Assistant for
TechNova Pvt. Ltd.

Answer the user's question using the information
provided by the selected company tool(s) below.
If the user asked about multiple things, address
each part of their question using the matching
tool result.

Do not invent information. If something wasn't
covered by any tool, say so plainly rather than
guessing.

Conversation history:
{conversation}

Long-term memory:
{memory_context}

Tools used:
{", ".join(tool_names)}

Tool result(s):
{tool_result_text}

User question:
{question}

Give a concise and helpful answer.
"""
        else:
            prompt = f"""
You are an intelligent Office Assistant for
TechNova Pvt. Ltd.

Answer the user's question naturally.

Use the conversation history and long-term memory
when useful.

Do not invent company-specific information.

Conversation history:
{conversation}

Long-term memory:
{memory_context}

User question:
{question}

Give a concise and helpful answer.
"""

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        answer = response.text

        if "policy" in tool_names and policy_sources:
            answer += "\n\nSources:\n"
            for source in policy_sources:
                answer += f"- {source}\n"

        if memory_item:
            answer = "I've saved that to long-term memory.\n\n" + answer

        self.short_term_memory.add_message("assistant", answer)

        return answer


if __name__ == "__main__":

    assistant = OfficeAssistant()

    print("\nOffice Assistant")
    print("----------------")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("You: ")
        if question.lower() == "exit":
            break
        answer = assistant.answer(question)
        print("\nAssistant:", answer)
        print()