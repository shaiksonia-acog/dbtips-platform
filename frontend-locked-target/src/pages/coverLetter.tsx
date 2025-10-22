import { FloatButton, Badge, ConfigProvider, Select } from "antd";
import CoverImage from "../assets/coverPage.png";
import { useMemo, useState } from "react";
import { useQuery } from "react-query";
import { fetchData } from "../utils/fetchData";
import { useNavigate } from "react-router-dom";
import LoadingButton from "../components/loading";
const { Option } = Select;
import ExportButton from "../components/exportButton";
import { AgGridReact } from "ag-grid-react";

console.log(
  "import.meta.env.VITE_TARGET_DOSSIER_URI",
  import.meta.env.VITE_TARGET_DOSSIER_URI
);
const baseUrl = import.meta.env.VITE_TARGET_DOSSIER_URI;
const navigateToTargetDossier = (path) => {
  const url = `${baseUrl}/${path}?target=IL31RA&indications="prurigo%20nodularis","asthma","chronic%20idiopathic%20urticaria"`;
  window.open(url, "_blank");
};
const indicationsList = [
  "Prurigo nodularis",
  "Alopecia areata",
  "Asthma",
  "Hidradenitis suppurativa",
  "Chronic idiopathic urticaria",
  "Dermatitis, atopic (Atopic eczema)",
];
const scrollIntoView = (id) => {
  const section = document.getElementById(id);
  const headerOffset = 80; // Height of the sticky header
  const elementPosition = section.getBoundingClientRect().top;
  const offsetPosition = elementPosition + window.scrollY - headerOffset;

  window.scrollTo({
    top: offsetPosition,
    behavior: "smooth",
  });
};

function transformDataWithScores(diseasesData: any, modalityFilter: string) {
  const evidenceScoreMap = {
    Approved: 4,
    "Successful trial": 3,
    "Ongoing trial": 2,
    Pathway: 1,
  };
  const result = [];
  const targetEvidenceCounts = new Map();

  Object.entries(diseasesData).forEach(([disease, entries]) => {
    (entries as any[]).forEach(({ Target, Modality, EvidenceType, Disease }) => {
      // Skip if modalityFilter is not 'all' and does not match the current Modality
      if (modalityFilter !== "All" && Modality !== modalityFilter) {
        return;
      }

      // Initialize evidence counts for the target if not exists
      if (!targetEvidenceCounts.has(Target)) {
        targetEvidenceCounts.set(Target, {
          Approved: 0,
          "Successful trial": 0,
          "Ongoing trial": 0,
          Pathway: 0,
        });
      }

      // Update evidence counts
      const counts = targetEvidenceCounts.get(Target);
      if (EvidenceType in counts) {
        counts[EvidenceType]++;
      }

      // Find or create a row for the target
      let row = result.find((r) => r.Target === Target);
      if (!row) {
        row = { Target };
        result.push(row);
      }

      // If modalityFilter is 'all', merge modalities by aggregating scores
      if (modalityFilter === "All") {
        row[Disease] = Math.max(
          row[disease] || 0,
          evidenceScoreMap[EvidenceType] || 0
        );
      } else {
        // Otherwise, differentiate by modality
        if (!row.Modality) row.Modality = Modality; // Set modality only for filtered cases
        row[Disease] = evidenceScoreMap[EvidenceType] || 0;
      }
    });
  });

  // Sort the results based on evidence counts
  result.sort((a, b) => {
    const countsA = targetEvidenceCounts.get(a.Target);
    const countsB = targetEvidenceCounts.get(b.Target);

    // Compare Approved counts
    if (countsA["Approved"] !== countsB["Approved"]) {
      return countsB["Approved"] - countsA["Approved"];
    }

    // Compare Successful trial counts
    if (countsA["Successful trial"] !== countsB["Successful trial"]) {
      return countsB["Successful trial"] - countsA["Successful trial"];
    }

    // Compare Ongoing trial counts
    if (countsA["Ongoing trial"] !== countsB["Ongoing trial"]) {
      return countsB["Ongoing trial"] - countsA["Ongoing trial"];
    }

    // Compare Pathway counts
    if (countsA["Pathway"] !== countsB["Pathway"]) {
      return countsB["Pathway"] - countsA["Pathway"];
    }

    // If all counts are equal, maintain stable sort by target name
    return a.Target.localeCompare(b.Target);
  });

  return result;
}

const statusMap = (value) => {
  if (value === "Approved") return "4";
  else if (value === "Successful trial") return "3";
  else if (value === "Ongoing trial") return "2";
  else if (value === "Pathway") return "1";
};

function convertToArray(data) {
  const result = [];
  Object.keys(data).forEach((disease) => {
    data[disease].forEach((record) => {
      result.push({
        ...record, // Add the disease key
        Status: statusMap(record["EvidenceType"]),
      });
    });
  });
  return result;
}
const evidenceColorMap = {
  4: "#43978D",
  3: "#7BE495",
  2: "#F9E07F",
  1: "#87CEEB",
  0: "white", // Default for 0 or missing values
};

const createDiseaseColumn = (field: string, headerName: string) => ({
  field,
  headerName: headerName=="Dermatitis, atopic (Atopic eczema)"?"Dermatitis, atopic (Atopic eczema)**":headerName,
  cellRenderer: (params: any) => {
    const value = params.data[field] || 0; // Default value is 0 if undefined
    const color = evidenceColorMap[value];
    return (
      <Badge color={color} className={color == "white" ? "coverLetter" : ""} />
    );
  },
  cellStyle: { textAlign: "center" },
  filter: false,
  sortable: false,
});
const diseaseNames = [
  "Alopecia areata",
  "Asthma",
  "Chronic idiopathic urticaria",
  "Hidradenitis suppurativa",
  "Prurigo nodularis",
  "Dermatitis, atopic (Atopic eczema)",
];
const CoverLetter = () => {
  const navigate = useNavigate();
  const navigateWithParams = (path, key) => {
    // Join indications with double quotes and commas
    const indications = indicationsList
      .map((indication) => `"${indication}"`)
      .join(",");

    // Navigate with target and formatted indications as query params
    navigate(`${path}?indications=${indications}`);

    // Scroll into view after navigation
    setTimeout(() => {
      scrollIntoView(key);
    }, 250);
  };
  const [selectedModality, setSelectedModality] = useState("All");
  const payload = {
    diseases: indicationsList,
  };
  const { data: indicationData, isLoading } = useQuery(
    ["coverLetter", payload],
    () => fetchData(payload, "/target-indication-pairs"),
    {
      enabled: !!indicationsList.length,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );
  console.log("indicationData", indicationData);
  const uniqueModality = useMemo(() => {
    if (indicationData) {
      return convertToArray(indicationData);
    }
    return [];
  }, [indicationData]);

  const processedData = useMemo(() => {
    if (indicationData) {
      return transformDataWithScores(indicationData, selectedModality);
    }
    return [];
  }, [indicationData, selectedModality]);
console.log("processedData", processedData);

  return (
    <div className="bg-gray-50 min-h-screen ">
      <header className="py-5 max-w-5xl mx-auto   text-black">
        <h1 className="text-5xl ">Cover note for disease dossier</h1>
        <p className="mt-2 text-lg">
          A comprehensive overview of key objectives and outcomes
        </p>
      </header>

      <main className="max-w-5xl mx-auto bg-white shadow-lg rounded-lg p-10 mt-1">
        <section className="mb-10">
          <h1 className="text-3xl font-semibold subHeading mb-4">
            Objectives & context
          </h1>
          <p className="text-gray-700 mb-6">
            This dossier is delivered from phases I and II of a multi-phase
            delivery plan to answer the following <b> two key questions</b>{" "}
            posed by Astria.
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-4">
            <li>
              <span className="font-semibold">
                Target identification across 6 indications of interest
              </span>
              <ul className="list-disc pl-6 space-y-2">
                <li>
                  For six indications of interest, analyze their respective
                  pathophysiological pathways.
                </li>
                <li>
                Identify and rank targets that could be effective across the greatest number of these indications.
                </li>
              </ul>
            </li>
            <li>
              <span className="font-semibold">OX40 pathway assessment</span>
              <ul className="list-disc pl-6 space-y-2">
                <li>
                  Evaluate and rank the six indications based on their
                  relationship to the OX40 pathway. Specifically, determine how effective OX40 inhibition could be for each indication.
                </li>
              </ul>
            </li>
          </ul>
        </section>

        <section className="mb-10">
          <h1 className="text-3xl font-semibold subHeading mb-4">
            Indications under consideration
          </h1>
          <div className="grid grid-cols-2 gap-4 mb-3">
            {[
              "Dermatitis, atopic (Atopic eczema)*",
              "Prurigo nodularis",
              "Alopecia areata",
              "Asthma",
              "Hidradenitis suppurativa",
              "Chronic Idiopathic urticaria",
            ].map((indication, index) => (
              <div key={index} className="bg-gray-100 p-4 rounded-lg  ">
                <p className="text-gray-800 font-medium">{indication}</p>
              </div>
            ))}
          </div>
          <p className="text-gray-700">
          * The dossiers include both <span className="underline"><a href="https://onlinelibrary.wiley.com/doi/full/10.1111/cea.13981" target="_blank" rel="noopener noreferrer" className="  hover:text-black hover:underline">Dermatitis, atopic and Atopic eczema due to  overlapping pathophysiology.</a></span>
          </p>
        </section>
   
        {/* <section className="mb-10">
          <h1 className="text-3xl font-semibold subHeading mb-4">
            Additional Astria-specific context
          </h1>
          <ul className="list-disc pl-6 text-gray-700 space-y-4">
            <li>Experience with antibody modality</li>
            <li>Existing pipeline assets for HAE & AD indications</li>
            <li>Exploring opportunities for bispecifics</li>
          </ul>
        </section> */}

        <section className="mb-10">
          <h1 className="text-3xl font-semibold subHeading mb-4">
            Overall plan
          </h1>
          <img
            src={CoverImage}
            alt="Cover Letter Illustration"
            className="rounded-lg shadow-md mx-auto"
            loading="lazy"
          />
        </section>

        <section className="mb-10">
          <h1 className="text-3xl font-semibold subHeading mb-4">
            Guide to using this dossier
          </h1>
          <p className="text-xl font-semibold text-gray-700">
            Phase I deliverable: Disease dossier
          </p>
          <p className="text-gray-700">
            You can click on the{" "}
            <span className="font-semibold text-gray-700">
              Navigate to disease dossier
            </span>{" "}
            button at the bottom right of this page to view the disease dossier.{" "}
          </p>

          <p className="text-gray-700 mb-6 font-semibold">
            {" "}
            Key sections in disease dossier:
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-4">
            <li>
              <span className="font-semibold cursor-pointer">
                Clinical evidence in{" "}
                <span
                  onClick={() =>
                    navigateWithParams(
                      "/market-intelligence",
                      "pipeline-by-indications"
                    )
                  }
                  className="underline "
                >
                  {" "}
                  market intelligence section:
                </span>
              </span>{" "}
              Availability, clarity and relevance of success/failure data for
              specific target-indication pairs. Nature & stage of competition.
              Reasons for termination incl. under-enrollment and adverse events.
            </li>
            <li>
              <span
                onClick={() =>
                  navigateWithParams("/literature", "knowledge-graph-evidence")
                }
                className="underline font-semibold cursor-pointer "
              >
                Pathway figures under literature section:
              </span>{" "}
              Look for types of inflammation involved, cell types of relevance,
              tissues (skin, lung, etc.) involved, itch-scratch or
              exposure-reaction processes.
            </li>
            <li>
              <span
                onClick={() => navigateWithParams("/data", "rnaSeq")}
                className="underline font-semibold cursor-pointer"
              >
                RNA-seq datasets
              </span>{" "}
              <span className="font-semibold">
                relevant to indications of interest:{" "}
              </span>
              <span>
                Look for datasets from studies on disease tissue in humans for
                the most relevant insights. Single-cell studies provide more
                granular insights compared to bulk studies.
              </span>
            </li>
            <li>
              <span
                className="font-semibold underline cursor-pointer"
                onClick={() =>
                  navigateWithParams("/model-studies", "model-studies")
                }
              >
                Animal model studies:
              </span>{" "}
              <span>
                {" "}
                Look for the gene perturbed and association type. The phenotype
                studies can be looked at by clicking on the “model” column.
              </span>
            </li>
          </ul>
          <p className="text-xl mt-2 font-semibold text-gray-700">
            Phase II deliverable: Target dossiers per target ({processedData?.length} target dossiers
            in total)
          </p>
          <p className="text-gray-700">
            You can also click on a target of interest in the{" "}
            <span className="font-semibold text-gray-700">
              Target-Indication Scorecard table
            </span>{" "}
            below to navigate to the respective target dossier. <br></br>
            Each target dossier can be accessed by clicking on the target name
            mentioned in the table. This dossier enables the researcher to
            further interrogate targets, providing further insights on target
            biology, structural biology, targetability, etc.
          </p>

          <p className="text-gray-700 mb-6 font-semibold mt-3">
            {" "}
            Key sections in target dossier:
          </p>
          <ul className="list-disc pl-6 text-gray-700 space-y-4">
            <li>
              <span>
                Target sequence and structural features, and functional
                annotations in{" "}
              </span>
              <span
                onClick={() => navigateToTargetDossier("target-biology")}
                className="underline font-semibold cursor-pointer "
              >
                target overview
              </span>{" "}
              section.
            </li>
            <li>
              <span>
                Phenotypic effects observed in target perturbation studies on
                animal models in{" "}
              </span>
              <span
                onClick={() => navigateToTargetDossier("literature")}
                className="underline font-semibold cursor-pointer "
              >
                evidence section.
              </span>
            </li>
            <li>
              <span className="font-semibold cursor-pointer">
                Target pipeline and patents listing in{" "}
                <span
                  onClick={() => navigateToTargetDossier("market-intelligence")}
                  className="underline "
                >
                  {" "}
                  market intelligence section:
                </span>
              </span>{" "}
              Nature & stage of competition & IP involving the target.
            </li>
            <li>
              <span>
                Assessments from targetability and safety perspectives in the{" "}
              </span>
              <span
                onClick={() => navigateToTargetDossier("target-assessment")}
                className="underline font-semibold cursor-pointer "
              >
                target assessment section.
              </span>
            </li>
          </ul>
        </section>
        <section className="mb-10">
          <h1 className="text-3xl font-semibold subHeading mb-4">
            Ask LLM to take multiple perspectives
          </h1>
          <span className="font-semibold mb-2">
            Perspectives to take when reviewing the information in this dossier
            & subsequent phases:
          </span>
          <ul className="list-disc pl-6 text-gray-700 space-y-4">
            <li>
              <span className="font-semibold">Patient outcomes:</span> Efficacy,
              potency
            </li>
            <li>
              <span className="font-semibold">Patient experience:</span> Safety,
              adverse events
            </li>
            <li>
              <span className="font-semibold">
                Commercial opportunities/challenges:
              </span>{" "}
              Nature and stage of competition, synergy (or lack of it) across
              indications with respect to market access & KOL influence
            </li>
            <li>
              <span className="font-semibold">
                Regulatory concerns to expect:
              </span>{" "}
              Dosages needed for availability & related tox burden
            </li>
            <li>
              <span className="font-semibold">Science readiness:</span> Data
              availability, tractability
            </li>
          </ul>
          <br />
          <span className="mt-4">
            To enable the investigation of data in this dossier with these
            perspectives and more, the dossier is integrated with AI Large
            Language Models (LLM) such as OpenAI ChatGPT. Currently, this
            facility is available with the{" "}
            <div
              className="w-[20px] h-[20px]"
              style={{ display: "inline-block" }}
            >
              <svg
                id="Layer_1"
                viewBox="0 0 512 512"
                xmlns="http://www.w3.org/2000/svg"
                data-name="Layer 1"
              >
                <path
                  d="m320.331 328.931a72.563 72.563 0 0 1 -128.659 0 12 12 0 1 1 21.279-11.1 48.561 48.561 0 0 0 86.1 0 12 12 0 1 1 21.283 11.1zm31.629-64.279a17.036 17.036 0 1 1 17.04-17.041 17.05 17.05 0 0 1 -17.043 17.041zm0-58.071a41.036 41.036 0 1 0 41.04 41.03 41.082 41.082 0 0 0 -41.038-41.03zm-191.921 58.071a17.036 17.036 0 1 1 17.029-17.041 17.055 17.055 0 0 1 -17.029 17.041zm0-58.071a41.036 41.036 0 1 0 41.03 41.03 41.084 41.084 0 0 0 -41.03-41.03zm325.132 120.15a19.742 19.742 0 0 1 -19.723 19.729h-7.2v-141.5h7.2a19.743 19.743 0 0 1 19.723 19.729v102.04zm-50.921 36.9v-175.841a42.727 42.727 0 0 0 -42.681-42.669h-271.139a42.727 42.727 0 0 0 -42.681 42.669v175.842a42.725 42.725 0 0 0 42.681 42.668h88.4a12.026 12.026 0 0 1 10.4 6l36.77 63.7 36.78-63.7a12 12 0 0 1 10.392-6h88.4a42.725 42.725 0 0 0 42.681-42.669zm-407.422-36.9v-102.04a19.743 19.743 0 0 1 19.722-19.729h7.2v141.5h-7.2a19.742 19.742 0 0 1 -19.722-19.729zm203.911-277.469a25.261 25.261 0 1 1 25.261 25.259 25.288 25.288 0 0 1 -25.26-25.259zm234.709 131.7h-7.548a66.768 66.768 0 0 0 -66.332-59.842h-123.568v-24.088a49.261 49.261 0 1 0 -24 0v24.088h-123.57a66.761 66.761 0 0 0 -66.33 59.842h-7.55a43.778 43.778 0 0 0 -43.723 43.729v102.04a43.776 43.776 0 0 0 43.723 43.729h7.55a66.761 66.761 0 0 0 66.33 59.84h81.478l43.7 75.7a12 12 0 0 0 20.783 0l43.709-75.7h81.469a66.768 66.768 0 0 0 66.331-59.84h7.547a43.776 43.776 0 0 0 43.723-43.729v-102.04a43.777 43.777 0 0 0 -43.722-43.729z"
                  fill="#0b427e"
                  fill-rule="evenodd"
                />
              </svg>{" "}
            </div>{" "}
            "Ask LLM" button in the{" "}
            <span
              className=" underline cursor-pointer"
              onClick={() =>
                navigateWithParams("/market-intelligence", "approvedDrug")
              }
            >
              clinical trials
            </span>
            ,{" "}
            <span
              className=" underline cursor-pointer"
              onClick={() =>
                navigateWithParams("/literature", "literature-evidence")
              }
            >
              literature{" "}
            </span>{" "}
            and{" "}
            <span
              className=" underline cursor-pointer"
              onClick={() => navigateWithParams("/data", "rnaSeq")}
            >
              RNA-seq{" "}
            </span>{" "}
            datasets related sections.
          </span>
        </section>

        <section className="mb-10">
          <ConfigProvider
            theme={{
              components: {
                Badge: {
                  statusSize: 20,
                },
              },
              token: {
                colorBorderBg: "#black",
              },
            }}
          >
            <h1 className="text-3xl font-semibold subHeading mb-4">
              Target-indication scorecard snapshot <sup>*</sup>
            </h1>
            <p className="my-3 text-gray-800">
              Target-indication pairs shortlisted after Phase II of the project.{" "}
              <br></br>
              Targets listed below have been filtered on the basis of finding
              evidence supported by its implication in atleast 2 indications.{" "}
              <br></br>
              <p>These evidence types are derived from clinical data and disease
              pathways (from literature).</p>
              <span className="font-semibold ">
                Targets have been prioritized in the
                following order:{" "}
              </span>
              <Badge color="#43978D" text="Approved" />
              {", "}
              <Badge color="#7BE495" text="Successful trial" />
              {", "}
              <Badge color="#F9E07F" text="Ongoing trial" />
              {", "}
              <Badge color="#87CEEB" text="Pathway" />
              {", "}
              <Badge color="white" text="No data" className="coverLetter" />
            </p>

            {isLoading && <LoadingButton />}
            {processedData.length && uniqueModality && (
              <div id="coverLetter">
                <div className="flex justify-between mb-4">
                  <div>
                    <span className="mt-1 mr-2">Filter by modality: </span>

                    <Select
                      defaultValue="All"
                      style={{ width: 200 }}
                      onChange={(value) => setSelectedModality(value)}
                    >
                      <Option value="All">All</Option>
                      {[
                        ...new Set(
                          uniqueModality.map((entry) => entry.Modality)
                        ),
                      ].map((modality) => (
                        <Option key={modality} value={modality}>
                          {modality}
                        </Option>
                      ))}
                    </Select>
                  </div>
                  <ExportButton
                    indications={indicationsList}
                    fileName="Target-Indication-Pairs"
                    endpoint="/target-indication-pairs"
                  />
                </div>
                <div className={`ag-theme-quartz w-full `}>
                  <AgGridReact
                    rowData={processedData}
                    columnDefs={[
                      {
                        field: "Target",
                        flex: 1.5,
                        cellRenderer: (params) => {
                          const values =
                            typeof params.value === "string"
                              ? params.value.split(" / ")
                              : [];
                          const baseUrl =
                            import.meta.env.VITE_TARGET_DOSSIER_URI || "";

                          const handleClick = (target) => {
                            const queryIndications = Object.keys(params.data)
                              .filter(
                                (key) =>
                                  key !== "Target" &&
                                  key.toLowerCase() !== "modality" &&
                                  params.data[key] !== undefined
                              )
                              .flatMap((disease) => {
                                if (
                                  disease ===
                                  "Dermatitis, atopic (Atopic eczema)"
                                ) {
                                  // Add two diseases instead of the original one
                                  return [
                                    "\"atopic eczema\"",
                                    "\"dermatitis, atopic\"",
                                  ];
                                }
                                return [`"${disease}"`]; // Add literal double quotes around each disease name
                              })
                              .join(",");
                           
                            const url = `${baseUrl}/?target=${target}&indications=${queryIndications}`;

                            window.open(url, "_blank");
                          };

                          return (
                            <div>
                              {values.length === 1 ? (
                                // If there's only one value, render it as plain text
                                <a
                                  href={baseUrl}
                                  onClick={(e) => {
                                    e.preventDefault();
                                    handleClick(values[0]);
                                  }}
                                >
                                  {values[0]}
                                </a>
                              ) : (
                                // Render the first value as plain text and the second value as a button
                                <>
                                  <span>{values[0]}</span>
                                  <span> / </span>
                                  <a
                                    href={baseUrl}
                                    onClick={(e) => {
                                      e.preventDefault();
                                      handleClick(values[1]);
                                    }}
                                  >
                                    {values[1]}
                                  </a>
                                </>
                              )}
                            </div>
                          );
                        },
                      },

                      ...diseaseNames.map((disease) =>
                        createDiseaseColumn(
                          disease,
                          disease
                        )
                      ),
                    ]}
                    defaultColDef={{
                      filter: true,
                      floatingFilter: true,
                      wrapHeaderText: true,
                      flex: 1,
                      autoHeaderHeight: true,
                      autoHeight: true,
                      sortable: true,
                      wrapText: true,
                      cellStyle: {
                        whiteSpace: "normal",
                        lineHeight: "20px",
                      },
                    }}
                    domLayout="autoHeight"
                  />
                </div>
              </div>
            )}
          </ConfigProvider>
          <p className="text-gray-800 mt-3">
            <span className="text-lg">*</span> Modalities for targets supported solely by "Pathway" evidence have been inferred based on their respective ongoing clinical trials related to autoimmune conditions.{" "}
            {/* <span
              className="underline cursor-pointer"
              onClick={() => navigateToTargetDossier("target-assessment")}
            >
              Target Assessment section
            </span> */}
             <br></br>
            <span className="text-lg">*</span> Omics evidence & analysis from
            subsequent phases yet to be factored in for further scoring the
            targets
          </p>
          <p className="text-gray-700">
          <span className="text-lg">**</span>  The dossiers include both <span><a href="https://onlinelibrary.wiley.com/doi/full/10.1111/cea.13981" target="_blank" rel="noopener noreferrer" className="underline hover:text-black hover:underline">Dermatitis, atopic and Atopic eczema due to overlapping pathophysiology.</a></span>
          </p>
        </section>
        <section className="mb-10">
          <h2 className="text-3xl font-semibold subHeading mb-4">
            What&rsquo;s coming next?
          </h2>
          <ul className="list-disc pl-6 text-gray-700 space-y-4">
            <li>
            Bringing additional resources to get the score 3 (Successful clinical trial) for target. 
            </li>
            <li>
            Transcriptomic data portal (DISTILL™)
              <ul className="list-disc pl-6 space-y-2">
               
                <li>
                Displaying immune modules per indication.
                </li>
                <li>
                Differentially expressed genes per disease indication.

                </li>
              </ul>
            </li>
            <li>
              Enhancing the existing Ask LLM capability to deeply interrogate
              existing disease and target dossiers in the following manner:
              <ul className="list-disc pl-6 space-y-2">
               
                <li>
                  Ability to orchestrate multiple sections within a dossier to
                  interrogate and ask questions to investigate the data
                </li>
              </ul>
            </li>
           
          </ul>
        </section>
      
      </main>

      <FloatButton
        description="Navigate to dossier"
        type="primary"
        shape="square"
        style={{ width: "200px" }}
        className="fixed bottom-5 right-5 shadow-lg"
        onClick={() => navigate("/home")}
      />
    </div>
  );
};

export default CoverLetter;
