import os
import logging
import google.generativeai as genai
from schema_handler import load_schema, store_all_table_structures
from deep_translator import GoogleTranslator

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Set up logging
logging.basicConfig(level=logging.INFO)
translator = GoogleTranslator(source='auto', target='en')

def translate_to_english(text):
    """
    Translates input text to English while keeping table names intact.
    """
    try:
        return translator.translate(text)
    except Exception as e:
        return text  


SQL_PROMPT = """
You are an expert MySQL administrator. Convert the given natural language request into a valid MySQL query.
The SQL database consists of multiple tables like STUDENT, COLLEGE, FACULTY with their respective columns.
You can create more tables, delete any table, perform JOIN operations as well as use aggregate functions,and many more if the user say so.
Rules:
1. Always use valid table and column names from the schema.
2. If the table exists in the schema file, use its column names.
3. Never assume column names—always refer to the schema.
4. Add LIMIT 100 to SELECT queries unless specified otherwise.
5.when there is "schema" in prompt then it should be used as "describe".
6.strictly provide sql query without any extra text.
7.if query is something like "show student table" use it as "SELECT * FROM student;". 
8.show schema means describe the table.
9.table ka schema dikhao means describe the table.
10.for any query of create use create if not exist with the given fields.
11. always take each input as lowercase strictly.
"""

def get_gemini_response(prompt):
    store_all_table_structures(force_update=True)  #   Ensure schema is fresh

    schema = load_schema()
    translated_prompt = translate_to_english(prompt)

    mentioned_tables = [table for table in schema.keys() if table.lower() in translated_prompt.lower()]
    if mentioned_tables:
        table_details = "\n".join(
            [f"Table `{table}`: Columns → {', '.join(schema[table].keys())}" for table in mentioned_tables]
        )

        relationship_details = []
        for table in mentioned_tables:
            for col, data in schema[table].items():
                if data.get("foreign_key"):
                    relationship_details.append(f"Column `{col}` in `{table}` links to {data['foreign_key']}")

        translated_prompt += f"\n\nSchema Details:\n{table_details}"
        if relationship_details:
            translated_prompt += f"\n\nTable Relationships:\n" + "\n".join(relationship_details)

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([SQL_PROMPT, translated_prompt])
        sql_query = response.text.strip().replace("```sql", "").replace("```", "").strip()
        return sql_query
    except Exception as e:
        return f"AI Error: {str(e)}"
