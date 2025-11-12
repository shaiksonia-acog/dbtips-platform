from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any, List, Union, Optional
import os
from redis import Redis
import re
import json
import shutil
import hashlib
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
# from langchain_experimental.agents import create_pandas_dataframe_agent
from agent import create_pandas_dataframe_agent
from langchain.agents import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks import BaseCallbackHandler
# from python import PythonAstREPLTool
from langchain_core.messages import AIMessage, HumanMessage
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from prompts import get_prompt_for_datasets
import pandas as pd
from io import StringIO
from os import getenv
from access_web import access_web
from tools import query_clinical_trial_data,query_inclusion_exclusion_criteria
import requests
from requests.auth import HTTPBasicAuth

PATIENT_STORIES_URL = os.getenv('PATIENT_STORIES_URL')
username = os.getenv('username')
password = os.getenv("password")

# State to store agent steps and chat history
app_state = {
    "steps": [],
    "chat_history": [],
    "data":[],
    "target_data": {},
    "patient_stories_disease": None
}

class PoorPyHandler(BaseCallbackHandler):
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        pass

    def on_tool_end(self, output: Any, **kwargs: Any) -> Any:
        print(output)
    
    pass

api_key=os.getenv('OPENAI_API_KEY')
llm = ChatOpenAI(model="gpt-4o", api_key=api_key, temperature=0.5)


## FAST API
class RequestBody(BaseModel):
    prompt: str 

class summaryRequest(BaseModel):
    contextVariables: Dict[str, Dict[str, Union[str, List[str]]]]
    selected_ctx: List[str] = Field(default_factory=list)

class Message(BaseModel):
    role: str
    message: Union[str, Dict]
    timestamp: str


class Conversation(BaseModel):
    id: str
    chat_name: str
    chat: List[Message]
    notes: str
    selected_ctx: List[str]
    summaryPrompt: Optional[str] = None 
    summaryContent: Optional[Dict] = None  
    dataSource: Optional[str] = None 
    contextVariables: Dict[str, Any]

class ConversationToSave(BaseModel):
    id: str
    chat_name: str
    chat: List[Message]
    notes: str
    selected_ctx: List[str]
    dataSource: Optional[str] = None 
    contextVariables: Dict[str, Any]

class UpdateContextRequest(BaseModel):
    chat: List[Message]
    summary_prompt: str
    summary_response: Dict
    context_variables:Dict[str, Any]



app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Redis connection for caching conversations
def get_redis() -> Redis:
    return Redis(host=getenv("REDIS_HOST", None), port=6379, db=0, decode_responses=True)


system_prompt="""
Consider yourself a subject matter expert who is assisting a scientist in the biopharma industry with target identification for for one or multiple diseases. 

Your task is to query the corresponding preloaded pandas dataframes in memory to answer the user's questions. If the necessary data is not available, use the available tools accordingly.

While accesing the data or using tools, you must follow the below instructions exactly:

### Accessing Data
    1. **Use Only the Preloaded Dataframes**  
    Do not create or generate any sample dataframes. Instead, query the actual, preloaded pandas dataframes that exist in your environment.
    2. **Understand the Data**  
    If you need to see how a dataframe is structured, obtain a sample of 5 rows using methods like `.head()`. This helps you understand the dataframe’s columns, data types, and the type of data it stores.
    3. **Choose the Right Dataframe(s)**  
    Select the most appropriate dataframe(s) to answer the question. If multiple dataframes are necessary to combine insights, you may query each as needed.
    4. **Use `.copy()`**  
    If you create any subset of a dataframe, always use `.copy()` to avoid modifying the original data.
    5. **Avoid Mentioning Dataframe Names**  
    Do not reveal the actual dataframe names in your final answer. Simply provide the relevant insights without referencing the dataframes directly by name.
    6. **Case Sensitivity**  
    Be mindful of case sensitivity when filtering or matching values in a dataframe (e.g., “Asthma” is not the same as "asthma").

### Using the `access_web` Tool
    1. **When to Use the access_web Tool:**  
        - `For Latest or Real-Time Information`: Use the tool whenever the user requests up-to-date information that cannot be answered using internal knowledge or accessible dataframes.
        - `When URLs or Sources Are Provided`: If the user includes URLs or mentions specific online sources, pass the entire `query as-is to the access_web tool` without any modifications.
        - `When Internal Resources Are Insufficient`: If the user's query cannot be answered using internal knowledge or available dataframe(s), construct a precise query to retrieve relevant information.
    2. **Instructions using access_web Tool
        - `Preserve the User's Query`: The access_web tool is equipped with an LLM and is fully capable of understanding and handling the user's intent directly. Do not analyze, simplify, or reformat the query before passing it to the tool.
        - `Include User Intent`: Always include the user's explicit intent in the query to ensure the tool retrieves the most relevant information (e.g., "summarize sections related to environmental impacts").
        - `Batch Process URLs`: If the user provides multiple URLs or sources, pass them all at once to allow the tool to process and consolidate the results efficiently.

### Analysis Approach
    - Understand the question and use the corresponding dataframe and tools available in your environment as needed
    - Elaborate on your results and provide reasoning using your expertise in genetics and target identification.
    - Draw meaningful connections between the data and biological pathways or implications for drug development.
    - Ensure that responses address **all the specific points** outlined in the user’s question, including detailed reasoning and context.
    - `unless explicitly asked, DO NOT format your answer and always reply in plain text`.

### Visualization Standards
    - Use Plotly to create interactive plots (e.g., with hovers, sliders, or buttons).
    - Generate a unique filename for each plot by appending a random 6-number suffix. Use Python's random module to generate this suffix
    - Save plots to a `.html` file (e.g., `fig.write_html('filename_unique_id.html')`).
    - Do not use the `.show()` method. Execute the code and include the output file name in your response. 
    - For diagrams such as ER (Entity-Relationship) diagrams, use Markdown with appropriate formatting (e.g., `Mermaid` syntax) instead of HTML or visual libraries. 

### Code Execution
    - Always execute your code using the PythonAstREPLTool and include the results in your response to ensure accuracy.

### Non-Code Responses
    - For non-code questions, provide a detailed reasoning-based response that uses your prior knowledge to address the query comprehensively.

### Important 
    - Always call PythonAstREPLTool with existing dataframes. DO NOT create new dataframes.
"""


df_descriptions = {
    "rnaseq_df": """**rnaseq_df**:
This dataframe lists all publicly available single-cell and bulk RNA sequencing studies of relevance to the disease (e.g., asthma). It can be used to analyze and infer the transcriptomic landscape of targets associated with the disease. Study-level columns (GseID, Title, Platform, Design, Organism, StudyType) are repeated for each sample within the same study. When analyzing the data, consider and return only the unique values of GseID columns to identify distinct studies.
""",
    "pipeline_indications_df": """**pipeline_indications_df**:
This df offers a comprehensive overview of drug candidates, categorized by indication, development status, and mechanism of action, based on data from ongoing and completed clinical trials. It supports scientists in validating drug targets across modalities and indications.
""",
    "literature_df": """**literature_df**:
This df provides a recent collection of disease research reviews for understanding the pathophysiology and therapeutic landscape of the disease.
""",
    "patient_stories_df": """**patient_stories_df**:
This dataframe provides the details about the Patient Stories suffering from a disease which includes: history, medical condition, patient's family details, Doctors details etc.""",
    
    "gwas_studies_df": """**gwas_studies_df**:
This dataframe provides the GWAS Studies information of a disease which includes details like: Traits, Summary Statistics, Study Accession, Authors etc.
""", 
    "gwas_associations_df": """**gwas_associations_df**:
This dataframe provides the GWAS Association information of a disease which includes details like: Variant and Risk Allele, rsID, Mapped gene(s), RAF etc""",
    
    "literature_df": """**Literature**"
This dataframe provides a recent collection of disease research reviews for understanding the pathophysiology and therapeutic landscape of the disease.""",

    "pipeline_target_df":"""**Pipeline by Targets**
This dataframe provides clinical precedence for drugs with investigational or approved indications targeting a specific gene according to their curated mechanism of action."""

}

#################### Helper functions ###################################################

def get_format_instructions_for_summary():
    summary_schema = ResponseSchema(
        name="summary",
        description=(
            "Provide a detailed summary of the data (as plain text), covering all important points. "
            "Ensure the summary is structured with headings and bullet points for clarity. "
            "Analyze the results comprehensively, include insights, and draw meaningful conclusions. "
            "**Do NOT include** key_topics_with_questions in this section."
        ),
        type="text"
    )

    key_topics_with_questions_schema = ResponseSchema(
        name="key_topics_with_questions",
        description=(
            "A JSON object where each key represents a topic and its value is a list of questions "
            "the user can ask to explore that topic further. "
            "Ensure that topics are relevant to the data and insightful for deeper exploration."
        ),
        type="object"
    )

    response_schemas = [summary_schema, key_topics_with_questions_schema]
    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

    # Generate format instructions
    format_instructions = output_parser.get_format_instructions()

    return output_parser,format_instructions

def get_html_file_urls(output_text):
    """Extracts HTML filenames and checks if they exist in the current directory.
    If they exist, moves them to the 'static' directory and returns unique URLs."""
    html_filenames = re.findall(r'\b\w+\.html\b', output_text)
    html_urls = set()  
    
    static_dir = "static"
    os.makedirs(static_dir, exist_ok=True)

    for filename in html_filenames:
        if os.path.isfile(filename):
            dest_path = os.path.join(static_dir, filename)
            
            if os.path.isfile(dest_path):
                print(f"File {filename} already exists in {static_dir}, skipping move.")
            else:
                shutil.move(filename, dest_path)
                print(f"Moved {filename} to {static_dir}")
        if os.path.isfile(os.path.join(static_dir, filename)):
            html_urls.add(f"/static/{filename}") 

    return list(html_urls)


def generate_cache_key_for_summary(context_variables: Dict[str, Dict[str, str]], selected_ctx: List[str]) -> str:
    sorted_ctx_ids = sorted(selected_ctx)
    filtered_context = {
        ctx_id: {k: v for k, v in context_variables[ctx_id].items() if k != "data"}
        for ctx_id in sorted_ctx_ids
        if ctx_id in context_variables
    }
    serialized_data = json.dumps({
        "selected_ctx": sorted_ctx_ids,
        "context_variables": filtered_context
    }, sort_keys=True)
    
    # Add a static identifier for summary keys
    summary_identifier = "summaryKey"
    full_data = f"{summary_identifier}:{serialized_data}"
    
    return hashlib.sha256(full_data.encode()).hexdigest()


def generate_prompt(selected_ctx: List[str], context_variables: Dict[str, Dict[str, str]]) -> str:
    selected_ctx_set = frozenset(selected_ctx)
    
    # Get the corresponding prompt template
    # prompt_template = PROMPT_TEMPLATES.get(selected_ctx_set)
    prompt_template = get_prompt_for_datasets(selected_ctx,context_variables)
    
    if not prompt_template:
        raise ValueError(f"No prompt template found for selected_ctx: {selected_ctx}")
    
    summary_prompt = ChatPromptTemplate.from_template(template=prompt_template)
    
    placeholders = {}
    for ctx in selected_ctx_set:
        if ctx in context_variables:
            for key, value in context_variables[ctx].items():
                placeholder_key = f"{ctx}_{key}"
                if placeholder_key in prompt_template: 
                    placeholders[placeholder_key] = value

    # Fill placeholders in the prompt template
    try:
        return summary_prompt.format_messages(**placeholders)
    except KeyError as e:
        raise ValueError(f"Missing placeholder in contextVariables: {e}")
    
def get_agent_executor(data):
    agent_executor = create_pandas_dataframe_agent(
            llm=llm,
            df=data,
            df_descriptions=df_descriptions,
            agent_type="openai-tools",
            prefix=system_prompt,
            verbose=True,
            allow_dangerous_code=True,
            max_iterations=5,
            include_df_in_prompt=True,
            return_intermediate_steps=True,
            extra_tools=[access_web,query_clinical_trial_data,query_inclusion_exclusion_criteria]
        )
    return agent_executor

def add_additional_topics_if_needed(response_object: dict, selected_ctx: str) -> dict:
    """Adds additional topics and questions based on specific IDs in selected_ctx."""
    additional_topics = {
        "pipeline_indications": {
            "Competitive Analysis": [
                "What are the major biopharma and biotech companies currently active in drug development for given diseases and what are the phases of development (e.g., preclinical, clinical trials: Phase 1, 2, 3, 4 or approved) for their pipeline candidates? Provide the results in the form of a table.?",
                "How do competitor drugs targeting the same indication differentiate based on their mechanism of action, delivery methods, or other unique attributes? Provide the results in the form of a table."
            ],
            "Trial Analysis": [
                "How do clinical endpoints and patient cohort characteristics influence the success or failure of clinical trials for specific targets? ",
                "What are the key differences in trial design, endpoints, or cohort characteristics between successful and failed clinical trials for the same targets? Provide the results in the form of a table."
            ]
        },
        "pipeline_target": {
            "Insights from clinical trials": [
                "How does the mechanism of action of late-phase candidates compare to competitors in terms of innovation and clinical outcomes?",
                "How do the competing trials stratify patients based on factors such as inclusion/exclusion criteria, trial summary, responder-non responder patients, biomarkers, primary and secondary endpoints used in trials?",
                "Are there ongoing trials exploring the targets in combination with other agents (e.g., immune checkpoint inhibitors)?"
            ]
        },
        
    }

    for key, topics in additional_topics.items():
        if key in selected_ctx:
            for topic, questions in topics.items():
                if "key_topics_with_questions" not in response_object["summary_text"]:
                    response_object["summary_text"]["key_topics_with_questions"] = {}
                response_object["summary_text"]["key_topics_with_questions"] = {
                        topic: questions,
                        **response_object["summary_text"]["key_topics_with_questions"],
                    }
    return response_object


############################ Endpoints ##############################################

@app.post("/summarise-text")
async def summarise_text(request: summaryRequest, redis_conn: Redis = Depends(get_redis)):
    cache_key = generate_cache_key_for_summary(request.contextVariables, request.selected_ctx)
    try:
        cached_response = redis_conn.get(cache_key)
        dataframes = {}

        for key, value in request.contextVariables.items():
            df = pd.read_csv(StringIO(value["data"].strip()), sep="," if "," in value["data"] else "\t")
            dataframe_name = f"{key}_df"
            dataframes[dataframe_name] = df

        print(dataframes)

        app_state['data'] = dataframes
        if cached_response:
            cached_response = json.loads(cached_response)
            # update llm context
            app_state["chat_history"].append(HumanMessage(content=cached_response["summary_prompt"]))
            app_state["chat_history"].append(AIMessage(content=json.dumps(cached_response["summary_text"])))
            return cached_response

        # If no cached response, generate summary
        output_parser, format_instructions = get_format_instructions_for_summary()
        messages=generate_prompt(request.selected_ctx, request.contextVariables)
        summary_prompt=messages[0].content
        messages[0].content += f"\n\n{format_instructions}"
        agent_executor=get_agent_executor(app_state["data"])
        # print(messages)
        # print(format_instructions)
        response = agent_executor.invoke({"input": messages, "chat_history": app_state["chat_history"][-6:]})
        try:
            response_as_dict = output_parser.parse(response["output"])
            if not isinstance(response_as_dict.get("summary"), str):
                raise ValueError("Expected summary as plain text, but got incorrect format.")
        except Exception as e:
            print(f"Parsing error: {e}")
            
            # Reattempt with explicit instruction
            retry_message = f"""
            The summary must follow this format strictly:
            {format_instructions}
            
            Ensure the response is properly structured and contains all required fields.
            """
            messages.append(HumanMessage(content=retry_message))
            response = agent_executor.invoke({"input": messages, "chat_history": app_state["chat_history"][-6:]})

            try:
                response_as_dict = output_parser.parse(response["output"])
                if not isinstance(response_as_dict.get("summary"), str):
                    raise ValueError("Expected summary as plain text, but got incorrect format.")
            except Exception as e:
                print(f"Retry failed: {e}")
                raise HTTPException(status_code=500, detail="LLM failed to generate a properly formatted summary. Refresh and try again")

        response_object = {
            "summary_prompt":summary_prompt,
            "summary_text": response_as_dict
        }
        response_object = add_additional_topics_if_needed(response_object, request.selected_ctx)
        app_state["chat_history"].append(HumanMessage(content=response_object["summary_prompt"]))
        app_state["chat_history"].append(AIMessage(content=json.dumps(response_object["summary_text"])))

        # Cache the full response object
        redis_conn.set(cache_key, json.dumps(response_object))

        return response_object
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error fetching summary text: {str(e)}")


@app.post("/update-context")
async def update_context(data: UpdateContextRequest):
    try:
        # Combine inputs to form the updated chat history
        chat_history = []
        if(data.summary_prompt!=''):
            chat_history.append(HumanMessage(content=data.summary_prompt))
            chat_history.append(AIMessage(content=json.dumps(data.summary_response)))

        for item in data.chat[-4:]:
            if(item.role=="user"):
                chat_history.append(HumanMessage(content=item.message))
            else:
                chat_history.append(AIMessage(content=item.message["output"]))
        app_state["chat_history"] = chat_history
        # print("Updated chat history: ", app_state["chat_history"])
        dataframes = {}

        for key, value in data.context_variables.items():
            if 'patient_stories' == key:  
                app_state['patient_stories_disease'] = value['disease'][0]
            csv_data = value["data"].replace('\\"', '"')
            df = pd.read_csv(StringIO(csv_data.strip()), sep="," if "," in csv_data else "\t", index_col=False)
            
            dataframe_name = f"{key}_df"
            dataframes[dataframe_name] = df

        if 'patient_stories' not in data.context_variables:
            app_state['patient_stories_disease'] = None
        
        app_state['data'] = dataframes

        print("df to agent: ", app_state['data'])
            

        return {"message": "llm context updated successfully!!!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-text")
async def generate_text(request_body: RequestBody, redis_conn: Redis = Depends(get_redis)):
    final_prompt = request_body.prompt
    #Clean up unnecessary tags from the prompt
    final_prompt = re.sub(r'\[\/?DATA\]|\[\/?RESPONSE_FORMAT\]', '', final_prompt)
    question=final_prompt
    # print('printing app state data')
    # print(app_state['chat_history'])

    try:
        print(app_state["chat_history"])
        if app_state['patient_stories_disease']:
            headers = {"Content-Type": "application/json"}

            # Provide your LDAP credentials
            rag_url = f"{PATIENT_STORIES_URL}/query"
            print("disease", app_state['patient_stories_disease'])
            
            payload = {"query": question, "disease_name": app_state['patient_stories_disease'].replace(' ', '_')}
            response = requests.post(rag_url, json=payload, headers=headers, auth=HTTPBasicAuth(username, password))
            
            res = response.json()

            print(res.keys(), res)
            html_file_urls= get_html_file_urls(res["response"])
            app_state["chat_history"].append(HumanMessage(content=final_prompt))
            app_state["chat_history"].append(AIMessage(content=res["response"]))

            return {
            "output": res.get("response", "Default output is missing"),
            "svg_file_urls": html_file_urls
            }
        agent_executor=get_agent_executor(app_state['data'])
        response = agent_executor.invoke({"input": question, "chat_history":app_state["chat_history"][-6:]})

        html_file_urls= get_html_file_urls(response["output"])
        # Append response to chat history
        app_state["chat_history"].append(HumanMessage(content=final_prompt))
        app_state["chat_history"].append(AIMessage(content=response["output"]))

        return {
            "output": response.get("output", "Default output if missing"),
            # "intermediate_steps": response.get("intermediate_steps", []),
            "svg_file_urls": html_file_urls
        }
    except Exception as e:
        print("Exception:", e)
        return {
            "output": "Cannot handle your request at this time :)!",
            "svg_file_urls": []
        }



# Endpoint to save a conversation to Redis
@app.post("/save_conversation")
async def save_conversation(conversation: ConversationToSave, redis_conn: Redis = Depends(get_redis)):
    try:
        conversation_key = f"conversation:{conversation.id}:{conversation.chat_name}"
        
        redis_conn.set(conversation_key, conversation.json())
        
        return {"message": "Conversation saved successfully"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error saving conversation: {str(e)}")


# Endpoint to list all conversations from Redis
@app.get("/list_conversations")
async def list_conversations(redis_conn: Redis = Depends(get_redis)):
    try:
        cursor = '0'
        conversations = []
        while cursor != 0:
            cursor, keys = redis_conn.scan(cursor=cursor, match="conversation:*")
            for key in keys:
                conversation_data = redis_conn.get(key)
                if conversation_data:
                    conversation = json.loads(conversation_data)
                    
                    selected_ctx = conversation["selected_ctx"]
                    context_variables = conversation["contextVariables"]
                    # print(selected_ctx, context_variables)
                    cache_key = generate_cache_key_for_summary(context_variables, selected_ctx)

                    cached_summary = redis_conn.get(cache_key)
                    if cached_summary:
                        cached_summary = json.loads(cached_summary)
                        conversation["summaryPrompt"] = cached_summary.get("summary_prompt", "")
                        conversation["summaryResponse"] = cached_summary.get("summary_text", "")

                    conversations.append(conversation)

        return conversations
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Error fetching conversations")

    

# Main entry to run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)