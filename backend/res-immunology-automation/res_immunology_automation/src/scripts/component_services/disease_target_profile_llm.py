from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import os


model = os.environ["LLM_MODEL"]
api_key = os.environ["OPENAI_API_KEY"]

def disease_target_descriptor(input_var: str, input_type: str) -> str:
    
    disease_template: str = """
        You are a biomedical data extraction assistant with expertise in sourcing disease-specific information from well-recognized patient advocacy groups, medical organizations or research institutions as sources.

        Your task is to gather comprehensive, in-depth information about the disease "{input_var}" from the following priority sources:

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

        Now, provide the JSON for "{input_var}" adhering to these guidelines.      
                  
        Output:
    """

    target_template: str = """
        You are an expert assistant for a translational scientist specializing in miRNA biology.

        Your task is to gather comprehensive, in-depth information about the microRNA **{input_var}** from the following priority sources:

            1. **Authoritative miRNA Databases and Gene Repositories** (e.g., miRBase, NCBI Gene, GeneCards, Orphanet for relevant rare disease links).
            2. **Peer-reviewed journals** (especially high-impact articles detailing functional studies).

            **Exclude Wikipedia.**

            ---

            ### **Output Requirements:**
            Provide the information **strictly** in the following JSON format. For each key:
            - **"data"**: Detailed information (strings for descriptions/prevalence; lists for synonyms/symptoms/types/phases).
            - **"source"**: The **primary source(s)** used, prioritized by **Authoritative Databases**. If not found, then only synthesize from other multiple sources, state: "[Source 1], [Source 2]".

            ---

            ### **Keys and Guidelines:**
            1. **Target Name**:  
            - Official name and any formal acronyms. don't give source for name  
            - *Example*:  
                ```json
                "Target Name": {{ "data": "miR-21-5p"}}
                ```

            2. **Target Description**:  
            - **Minimum 8–10 lines, but strictly $\le 15$ lines**, of in-depth description, covering:  
                - Identity & Biogenesis: Canonical name, accession, species; pri-miRNA genomic locus & host gene; pre-miRNA hairpin description.
                - Strands: Briefly explain 5p vs 3p strands, which is dominant/functional, and any known passenger-strand activity.
                - Disease Relevance: Identify the most strongly evidenced human disease association with brief justification (human biopsies, circulating miRNA, perturbation studies).
                - Mechanism: Describe in compact form the validated target genes, key signaling pathways, upstream stimuli, and cellular phenotypes influenced by the miRNA.
                - Pathophysiology Link: Summarize how these mechanisms contribute to disease initiation/progression/resolution.
                - Translational Notes: Mention any relevance as a biomarker, therapeutic target, or pathway node (concise).
            - *Example*:  
                ```json
                "Target Description": {{  
                "data": "The microRNA miR-33a (hsa-miR-33a-5p, MI0000735, Human) is intronic to the $SREBF2$ gene on $17p11.2$ (pri-miR-33a-2), sharing biogenesis with its host which encodes the sterol regulatory element-binding protein 2. Its 70-nucleotide pre-miRNA forms a canonical hairpin. The functional, dominant strand is miR-33a-5p, derived from the $5\text arm, while the passenger strand (miR-33a-3p) shows negligible or unconfirmed activity. Its most robust association is with Cardiovascular Disease, particularly Atherosclerosis, evidenced by elevated expression in human atherosclerotic plaques, perturbation studies in mouse models, and correlation with $HDL-C$ levels in circulation. Mechanism: miR-33a-5p is a key metabolic regulator. It targets and represses genes involved in cholesterol efflux, including $ABCA1$ and $ABCG1$, and promotes fatty acid synthesis by inhibiting $AMPK\alpha1$. Upstream stimuli include cholesterol depletion (via $SREBF2$) and $LXR$ activation. This leads to reduced $HDL$ formation and increased lipid accumulation, primarily in macrophages (foam cell formation). Pathophysiology Link: By suppressing $ABCA1/G1$, miR-33a directly impairs reverse cholesterol transport from macrophages, accelerating their transformation into foam cells, which is the hallmark of atherosclerotic plaque initiation and progression. Translational Notes: miR-33a is being explored as a therapeutic target for  using anti-miRs (Antagomirs) to increase $ABCA1$ expression and $HDL$ levels, functioning as a critical pathway node linking cholesterol homeostasis to inflammation.",
                "source": "Synthesized from miRBase and High-Impact Peer-Reviewed Literature"  
                }}
                ```

            3. **Synonyms**:  
            - Include official gene symbols, human specific, specific terms of family, Older or alternative gene symbol, MicroRNA Name, Mature/Functional Strand Names.  
            - *Example*:  
                ```json
                "Synonyms": {{ "data": ["MIR33A", "hsa-mir-33a", "miR-33", "MIR33", "MIRN33A", "hsa-miR-33a-5p"], "source": "miRBase" }}
                ```

            Output must be scientifically accurate, mechanistically rich, and strictly $\le 15$ lines paragraph for the description.
            
            ### **Example Output Structure** (for miR-33a):
            ```json
            {{
            "Target Name": {{ "data": "miR-33a-5p"}},
            "Target Description": {{ 
                "data": "The microRNA miR-33a (hsa-miR-33a-5p, MI0000735, Human) is intronic to the SREBF2 gene on 17p11.2 (pri-miR-33a-2), sharing biogenesis with its host which encodes the sterol regulatory element-binding protein 2. Its 70-nucleotide pre-miRNA forms a canonical hairpin. The functional, dominant strand is miR-33a-5p, derived from the 5' arm, while the passenger strand (miR-33a-3p) shows negligible or unconfirmed activity. Its most robust association is with Cardiovascular Disease (CVD), particularly Atherosclerosis, evidenced by elevated expression in human atherosclerotic plaques, perturbation studies in mouse models, and correlation with HDL-C levels in circulation. Mechanism: miR-33a-5p is a key metabolic regulator. It targets and represses genes involved in cholesterol efflux, including ABCA1 and ABCG1, and promotes fatty acid synthesis by inhibiting AMPK\u03b11. Upstream stimuli include cholesterol depletion (via SREBF2) and LXR activation. This leads to reduced HDL formation and increased lipid accumulation, primarily in macrophages (foam cell formation). Pathophysiology Link: By suppressing ABCA1/G1, miR-33a directly impairs reverse cholesterol transport from macrophages, accelerating their transformation into foam cells, which is the hallmark of atherosclerotic plaque initiation and progression. Translational Notes: miR-33a is being explored as a therapeutic target for CVD using anti-miRs (Antagomirs) to increase ABCA1 expression and HDL levels, functioning as a critical pathway node linking cholesterol homeostasis to inflammation.",
                "source": "Synthesized from miRBase and High-Impact Peer-Reviewed Literature"
            }},
            "Synonyms": {{ "data": ["MIR33A", "hsa-mir-33a", "miR-33", "MIR33", "MIRN33A", "hsa-miR-33a-5p"], "source": "miRBase, NCBI Gene"
            }}
            }}
            ```
            Now, provide the JSON for {input_var} adhering to these guidelines.            
            
            Output:
    """
    
    if input_type == "disease":
        template = disease_template
    elif input_type == "target":
        template = target_template
    prompt = PromptTemplate(template=template, input_variables=["input_var"])

    llm = ChatOpenAI(
        model_name=model,
        temperature=0,
        openai_api_key=api_key,
    )

    parser = JsonOutputParser()

    chain = prompt | llm | parser

    result = chain.invoke({"input_var": input_var})

    return result

if __name__ == "__main__":
    # disease_name = "Rheumatoid Arthritis"
    # result = disease_target_descriptor(disease_name, "disease")
    # print(result)

    target_miRNA_name = "miR-33a"
    result = disease_target_descriptor(target_miRNA_name, "target")
    print(result)