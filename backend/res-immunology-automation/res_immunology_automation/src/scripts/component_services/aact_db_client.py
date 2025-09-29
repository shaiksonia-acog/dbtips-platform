import os
import psycopg2
from dotenv import load_dotenv
from component_services.market_intelligence_service import get_mesh_term_for_disease
import logging

load_dotenv()

class DBClient:
    def __init__(self):
        self.host = os.getenv("AACT_DB_HOST")
        self.port = os.getenv("AACT_DB_PORT")
        self.userid = os.getenv("AACT_DB_USER")
        self.pwd = os.getenv("AACT_DB_PASSWORD")
        self.dbname = os.getenv("AACT_DB_NAME")  # Default to 'aact' if not set
        print(f"Host: {self.host}, Port: {self.port}, User: {self.userid}, DB: aact")
        self.connection = self.connect_to_db()
        print("Connected to AACT database")
        print("Initialized DBClient")
        
    def connect_to_db(self):
        print("Connecting to AACT database...")
        print(f"Host: {self.host}, Port: {self.port}, User: {self.userid}, DB: aact")
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.userid,
            password=self.pwd,
            dbname=self.dbname  # Updated to correct DB name
        )

    def fetch_data(self, disease_name):
        """
        Fetches clinical trial data for both the original disease name (name 1)
        and its MeSH term (name 2), merging results automatically for any disease.
        """
        mesh_term = get_mesh_term_for_disease(disease_name)
        if not mesh_term:
            mesh_term = ""
        logging.info(f"Found MeSH term: {mesh_term}")

        query = """
        WITH all_trials AS (
            -- Trials matching the original disease name (name 1)
            SELECT
                s.nct_id,
                c.downcase_name AS condition_name,
                s.phase,
                s.overall_status,
                s.source AS sponsor,
                s.source_class,
                s.official_title,
                STRING_AGG(i.name, ', ') AS drug_names,
                STRING_AGG(i.intervention_type, ', ') AS intervention_types
            FROM
                ctgov.conditions c
            JOIN
                ctgov.studies s ON c.nct_id = s.nct_id
            JOIN
                ctgov.interventions i ON s.nct_id = i.nct_id
            WHERE
                c.downcase_name = %s
                AND s.study_type = 'INTERVENTIONAL'
                AND i.intervention_type IN ('DRUG', 'BIOLOGICAL')
            GROUP BY
                s.nct_id, c.downcase_name, s.phase, s.overall_status, s.source, s.source_class, s.official_title

            UNION

            -- Trials matching the MeSH term (name 2)
            SELECT
                s.nct_id,
                bc.downcase_mesh_term AS condition_name,
                s.phase,
                s.overall_status,
                s.source AS sponsor,
                s.source_class,
                s.official_title,
                STRING_AGG(i.name, ', ') AS drug_names,
                STRING_AGG(i.intervention_type, ', ') AS intervention_types
            FROM
                ctgov.browse_conditions bc
            JOIN
                ctgov.studies s ON bc.nct_id = s.nct_id
            JOIN
                ctgov.interventions i ON s.nct_id = i.nct_id
            WHERE
                bc.downcase_mesh_term = %s
                AND s.study_type = 'INTERVENTIONAL'
                AND i.intervention_type IN ('DRUG', 'BIOLOGICAL')
            GROUP BY
                s.nct_id, bc.downcase_mesh_term, s.phase, s.overall_status, s.source, s.source_class, s.official_title
        )
        SELECT DISTINCT * FROM all_trials;
        """

        with self.connection.cursor() as cur:
            cur.execute(query, (disease_name.lower(), mesh_term.lower()))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
        return data
    
    def fetch_trials_for_drug_and_indication(self, drug_name, indication_name):
        """
        Fetches all clinical trial rows for a given drug and indication.
        Returns a list of dicts with all relevant columns.
        """
        query = f"""
                SELECT
            s.nct_id,
            STRING_AGG(DISTINCT bc.downcase_mesh_term, ', ') AS mesh_condition_names,
            STRING_AGG(DISTINCT c.downcase_name, ', ')       AS raw_condition_names,
            s.phase,
            s.overall_status,
            s.source AS sponsor,
            s.source_class,
            s.official_title,
            STRING_AGG(DISTINCT i.name, ', ') AS drug_names,
            STRING_AGG(DISTINCT i.intervention_type, ', ') AS intervention_types
        FROM
            ctgov.browse_conditions bc
        JOIN
            ctgov.conditions c
            ON bc.nct_id = c.nct_id
        JOIN
            ctgov.studies s
            ON bc.nct_id = s.nct_id
        JOIN
            ctgov.interventions i
            ON s.nct_id = i.nct_id
        WHERE
            (
                bc.downcase_mesh_term = %s
                OR c.downcase_name ILIKE ANY (%s)
            )
            AND s.study_type = 'INTERVENTIONAL'
            AND i.intervention_type IN ('DRUG', 'BIOLOGICAL')
            AND LOWER(i.name) LIKE %s
        GROUP BY
            s.nct_id, s.phase, s.overall_status, s.source, s.source_class, s.official_title;

        """
        indication_mesh_term = get_mesh_term_for_disease(indication_name)
        
        with self.connection.cursor() as cur:
            if not indication_mesh_term:
                cur.execute(query, (indication_name.lower(), drug_name.lower()))
            else:
                cur.execute(query, (indication_mesh_term.lower(), [indication_name.lower(), indication_mesh_term.replace(",", "").lower()], f"%{drug_name.lower()}%"))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
        return data

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            print("Connection to AACT database closed.")


if __name__ == "__main__":
    try:
        db_client = DBClient()
        # Example: test with "lung cancer" (replace with any disease you want)
        results = db_client.fetch_data("lung cancer")
        
        print(f"Number of trials found: {len(results)}")
        for trial in results[:5]:  # Show first 5 trials
            print(trial)
    except Exception as e:
        print("Error while testing DBClient:", e)

# def get_aact_db():
#     db = DBClient()
#     try:
#         yield db
#     finally:
#         db.close()