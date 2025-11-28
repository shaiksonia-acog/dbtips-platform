from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import os


model = os.environ["LLM_MODEL"]
api_key = os.environ["OPENAI_API_KEY"]

def disease_interpreter(disease_name: str,) -> str:
    template: str = """
        You are a biomedical data extraction assistant with expertise in sourcing disease-specific information from well-recognized patient advocacy groups, medical organizations or research institutions as sources.

        Your task is to gather comprehensive, in-depth information about the disease "{disease_name}" from the following priority sources:

        1. **Disease-specific organizations or well-recognized patient advocacy groups** (e.g., for Friedreich ataxia: https://www.ataxia.org/fa/ (National Ataxia Foundation); for autoimmune diseases: https://www.aarda.org/ or https://www.autoimmuneinstitute.org/): and any other type of diseases must have their sources 
        2. **Reputable medical sources like medical organizations or research institutions** if disease specific source or organization does not available
        3. **Peer-reviewed journals** if needed other than related website

        **Exclude Wikipedia.**

        ---

        ### **Output Requirements:**
        Provide the information **strictly** in the following JSON format. For each key:
        - **"data"**: Detailed information (strings for descriptions/prevalence; lists for synonyms/symptoms/types/phases).
        - **"source"**: The **primary source(s)** used, prioritized by Disease-specific organizations If not found, then only synthesize from other multiple sources, state: "[Source 1], [Source 2]".

        ---

        ### **Keys and Guidelines:**
        1. **Disease Name**:  
        - Official name and any formal acronyms. don't give source for name  
        - *Example*:  
            ```json
            "Disease Name": {{ "data": "Rheumatoid Arthritis (RA)"}}
            ```

        2. **Disease Description**:  
        - **Minimum 8–10 lines** of in-depth description, covering:  
            - Pathophysiology (e.g., genetic mutations, biological mechanisms).  
            - Primary affected systems (e.g., nervous system for neurological diseases).  
            - Key clinical hallmarks.  
        - *Example*:  
            ```json
            "Disease Description": {{  
            "data": "Rheumatoid arthritis (RA) is a chronic autoimmune disorder wherein the immune system mistakenly attacks the synovium—the lining of the membranes that surround the joints. This aberrant immune response leads to inflammation, causing the synovium to thicken, which can eventually result in cartilage and bone damage within the joint. The condition predominantly affects synovial joints, including those in the hands, wrists, and knees, and typically presents symmetrically. Beyond joint involvement, RA can manifest systemically, impacting organs such as the heart, lungs, and eyes. Clinical hallmarks include persistent joint pain, swelling, stiffness (notably in the morning or after periods of inactivity), fatigue, and, in some cases, the formation of rheumatoid nodules. If left untreated, RA can lead to joint deformity and significant functional impairment.",  
            "source": "Arthritis Foundation"  
            }}
            ```

        3. **Synonyms**:  
        - Include clinical terms, historical names, and abbreviations.  
        - *Example*:  
            ```json
            "Synonyms": {{ "data": ["RA", "Atrophic Arthritis"], "source": "Arthritis Foundation" }}
            ```

        4. **Prevalence**:  
        - Epidemiology (global/regional prevalence, incidence rates, demographics).  
        - Cite specific studies if available.  
        - *Example*:  
            ```json
            "Prevalence": {{ "data": "Globally, rheumatoid arthritis affects approximately 0.24% of the population. In the United States, the annual incidence is about 40 per 100,000 individuals. The disease is more prevalent in women than in men, with a lifetime risk of 3.6% for women compared to 1.7% for men. The prevalence increases with age, peaking between 65 to 80 years.", "source": "StatPearls - NCBI Bookshelf" }}
            ```

        5. **Symptoms**:  
        - List **all major symptoms**, prioritizing early vs. late-stage manifestations.  
        - *Example*:  
            ```json
            "Symptoms": {{  
            "data": [
            "Joint pain and tenderness",
            "Joint swelling and warmth",
            "Morning stiffness lasting longer than 30 minutes",
            "Fatigue",
            "Low-grade fever",
            "Loss of appetite",
            "Firm lumps (rheumatoid nodules) under the skin",
            "Joint deformity in advanced stages"
            ],  
            "source": "Mayo Clinic"  
            }}
            ```

        6. **Types**:  
        - Subtypes (e.g., genetic variants, clinical classifications).  
        - *Example*:  
            ```json
            "Types": {{ "data": ["Seropositive RA", "Seronegative RA", "Juvenile Rheumatoid Arthritis (JRA)"], "source": "Mayo Clinic", "Arthritis Foundation" }}
            ```

        7. **Phases**:  
        - Disease progression stages (if applicable).  
        - *Example*:  
            ```json
            "Phases": {{ "data": [
            "Early-stage RA: Initial inflammation without joint damage",
            "Moderate-stage RA: Inflammation begins to damage cartilage",
            "Severe-stage RA: Damage extends to bones; visible joint deformity",
            "End-stage RA: Inflammation subsides but joints no longer function"
            ], "source": "Cleveland Clinic" }}
            ```

        ---

        ### **Example Output Structure** (for a different disease):
        ```json
        {{
        "Disease Name": {{ "data": "Systemic Lupus Erythematosus"}},
        "Disease Description": {{ 
            "data": "Systemic Lupus Erythematosus (SLE) is a chronic autoimmune disease characterized by multisystem inflammation and the production of autoantibodies against nuclear antigens. The pathogenesis involves genetic predisposition (e.g., HLA-DR3), environmental triggers (e.g., UV light), and dysregulated B-cell and T-cell responses. Clinical manifestations range from mild (rash, arthritis) to severe (nephritis, neuropsychiatric involvement). The disease follows a relapsing-remitting course, with flares triggered by infections or stress. Females are disproportionately affected (9:1 ratio), particularly during reproductive years. Diagnostic criteria include anti-dsDNA antibodies, low complement levels, and biopsy-proven nephritis.",  
            "source": "AARDA, Lupus Foundation of America" 
        }},
        "Synonyms": {{ "data": ["SLE", "Lupus"], "source": "MedlinePlus" }},
        "Prevalence": {{"data": "Estimated 20–150 cases per 100,000 people globally; higher prevalence in African-American and Hispanic populations." , "source": "NIH Epidemiology Study (2022)" }},
        "Symptoms": {{
            "data": ["Malar rash", "Photosensitivity", "Renal dysfunction", "Arthritis", "Pleuritis"], 
            "source": "Johns Hopkins Lupus Center" 
        }},
        "Types": {{ "data": ["Cutaneous Lupus", "Drug-Induced Lupus", "Neonatal Lupus"], "source": "Lupus Research Alliance" }},
        "Phases": {{ "data": ["Flare", "Remission"], "source": "Clinical Rheumatology Journal" }}
        }}
        ```

        Critical Notes:

            • Prioritize well-recognized patient advocacy groups and disease-specific website , (e.g., ataxia.org or National Ataxia Foundation for friedreich ataxias; aarda.org or autoimmuneinstitute.org for autoimmune diseases.) go for this mentioned source only if these disease has been given 
            
            • Descriptions must be detailed and mechanistic (avoid simplistic summaries).
            
            • Cross-verify prevalence data with recent studies or registries.
            
            • For rare diseases, use Orphanet or NIH GARD as primary sources; for any  other type, go for their related source only first.

        Now, provide the JSON for "{disease_name}" adhering to these guidelines.      
                  
        Output:
    """
    prompt = PromptTemplate(template=template, input_variables=["disease_name"])

    llm = ChatOpenAI(
        model_name=model,
        temperature=0,
        openai_api_key=api_key,
    )

    parser = JsonOutputParser()

    chain = prompt | llm | parser

    result = chain.invoke({"disease_name": disease_name})

    return result