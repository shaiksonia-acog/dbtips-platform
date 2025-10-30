import { useEffect, useState, useMemo } from "react";
import { useQuery, useQueries } from "react-query";
import {
  Empty,
  Button,
  Segmented,
  ConfigProvider,
  message,
  Select,
} from "antd";
import { fetchData } from "../../utils/fetchData";
import { capitalizeFirstLetter } from "../../utils/helper";
import LoadingButton from "../../components/loading";
import { useChatStore } from "chatbot-component";
import BotIcon from "../../assets/bot.svg?react";
import axios from "axios";
import Table from "../../components/table";
import {
  preprocessGWASStudiesData,
  preprocessAssociationData,
} from "../../utils/llmUtils";
const { Option } = Select;
import ExportButton from "../../components/exportButton";
import ColumnSelector from "../../components/columnFilter";
import { filterByDiseases } from "../../utils/filterDisease";
import DiseaseFilter from "../../components/diseaseFilter";
const parseTsvData = (tsvText) => {
  const lines = tsvText.trim().split("\n");
  const headers = lines[0].split("\t");

  return lines.slice(1).map((line) => {
    const values = line.split("\t");
    const entry = {};

    headers.forEach((header, index) => {
      entry[header] = values[index];
    });

    return entry;
  });
};
function convertTODiseaseArray(data) {
  const result = [];

  for (const [disease, path] of Object.entries(data)) {
    if (
      typeof path === "string" &&
      path.includes("/app/res-immunology-automation/")
    ) {
      const mondoId =
        typeof path === "string"
          ? path.split("/").pop()?.split(".")[0]
          : undefined; // Extract mondoId from the file path
      result.push({ disease, mondoId });
    }
  }

  return result;
}

function convertToArray(data) {
  const result = [];
  const diseaseWithoutEFOID = [];
  Object.keys(data).forEach((disease) => {
    // Only process diseases with an array of study records
    if (Array.isArray(data[disease])) {
      data[disease].forEach((record) => {
        result.push({
          ...record,
          pubDate: record["Pub. date"] || null, // Safely access the publication date
          DiseaseArea: capitalizeFirstLetter(disease.replace(/_/g, " ")),
          disease: capitalizeFirstLetter(disease.replace(/_/g, " ")), // Add the disease key
        });
      });
    } else {
      diseaseWithoutEFOID.push(disease);
    }
  });

  return { result, diseaseWithoutEFOID };
}
const AssociatePlot = ({ indications, diseaseAreaFilter,target }) => {
  const [selectedDisease, setSelectedDisease] = useState([]);
  const [activeTab, setActiveTab] = useState("association");
  // const [diseaseFilterOptions, setDiseaseFilterOptions] = useState<string[]>([]);
  const [selectedDiseaseAreas, setSelectedDiseaseAreas] = useState(indications);
  const [columns, setColumns] = useState([]);
  const [defaultSelectedColumns, setDefaultSelectedColumns] = useState([]);
  const [selectedGene, setSelectedGene] = useState<string | undefined>();
  const [selectedAccession, setSelectedAccession] = useState([]);
  const [selectedColumnsGWASStudies, setSelectedColumnsGWASStudies] = useState([
    "DiseaseArea",
    "disease",
    "Association count",
    "First author",
    "Study accession",
    "pubDate",
    "Journal",
    "Title",
    "Reported trait",
    "Trait(s)",
    "Discovery sample ancestry",
    "Replication sample ancestry",
    "Summary statistics",
  ]);
  useEffect(() => {
    if (!diseaseAreaFilter) {
      setSelectedDisease(indications);
    }
    setSelectedDiseaseAreas(indications);
    if (target)
    setSelectedGene(target);
  }, [indications, diseaseAreaFilter,target]);
  const [selectedAssociationColumns, setSelectedAssociationColumns] = useState([
    "DiseaseArea",
    "mapped_diseases",
    "Study Accession",
    "Variant and Risk Allele",
    "pvalue",
    "RAF",
    "OR or BETA",
    "CI",
    "Mapped gene(s)",
    "Variant annotation"

  ]);
  const gwasColumnDefs = useMemo(
    () => [
      ...(diseaseAreaFilter
        ? [
            {
              field: "disease",
              headerName: "Disease Area",
            },
          ]
        : []),
      {
        field: "Association count",
        maxWidth: 120,
        valueGetter: (params) => {
          if (params.data["Association count"] === "Not available") return "0";
          else if (params.data["Association count"]) {
            return params.data["Association count"];
          } else return "0";
        },
        sort: "desc",
      },
      {
        field: "First author",
      },
      {
        field: "Study accession",
        cellRenderer: (params) => {
          return (
            <a
              href={`https://www.ebi.ac.uk/gwas/studies/${params.value}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {params.value}
            </a>
          );
        }
      },
      {
        field: "pubDate",
        filter: "agDateColumnFilter",
        headerName: "Pub. Date ",
        flex: 2,
      },
      {
        field: "Journal",
      },
      {
        field: "Title",
        minWidth: 200,
      },
      {
        field: "Reported trait",
      },
      {
        field: "Trait(s)",
      },
      {
        field: "Discovery sample ancestry",
      },
      {
        field: "Replication sample ancestry",
        flex: 2,
      },

      {
        field: "Summary statistics",
        cellRenderer: (params) => {
          if (params.value !== "NA") {
            return (
              <a href={params.value} target="_blank" rel="noopener noreferrer">
                FTP download
              </a>
            );
          } else return "Not available";
        },
      },
    ],
    [diseaseAreaFilter]
  );
  const associationColumnDefs = useMemo(
    () => [
      ...(diseaseAreaFilter
        ? [
            {
              field: "DiseaseArea",
              headerName: "Disease Area",
            },
          ]
        : []),
      {
        headerName: "Disease",

        field: "mapped_diseases",
        cellRenderer: (params) => {
          if (!params.value) return "";
          return params.value
            .map((val) => capitalizeFirstLetter(val))
            .join(" | ");
        },
      },
      {
        headerName: "Study Accession",
        field: "Study Accession",
        cellRenderer: (params) => {
          return (
            <a
              href={`https://www.ebi.ac.uk/gwas/studies/${params.value}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {params.value}
            </a>
          );
        }
      },
      {
        headerName: "Variant and Risk Allele",
        field: "Variant and Risk Allele",
      },
      {
        headerName: "p-value",
        field: "pvalue",
        agGridColumnType: "numericColumn",
        sort: "asc",
        filter: "agNumberColumnFilter",
        comparator: (valueA, valueB) => {
          // Handle null/undefined/empty
          if (!valueA && !valueB) return 0;
          if (!valueA) return 1;
          if (!valueB) return -1;

          // Extract exponents from scientific notation
          const getExponent = (val) => {
            const str = String(val).toUpperCase();
            const match = str.match(/E([+-]?\d+)/);
            if (!match) return 0; // Not in scientific notation
            return parseInt(match[1], 10);
          };

          const getCoefficient = (val) => {
            const str = String(val).toUpperCase();
            const match = str.match(/^([+-]?\d+\.?\d*)/);
            if (!match) return parseFloat(val);
            return parseFloat(match[1]);
          };

          const expA = getExponent(valueA);
          const expB = getExponent(valueB);

          // Compare by exponent first (larger exponent = larger number)
          if (expA !== expB) {
            return expA - expB;
          }

          // If exponents equal, compare coefficients
          const coefA = getCoefficient(valueA);
          const coefB = getCoefficient(valueB);
          return coefA - coefB;
        },
      },
      {
        headerName: "RAF",
        field: "RAF",
      },
      {
        headerName: "OR or BETA",
        field: "OR or BETA",
      },

      {
        headerName: "CI",
        field: "CI",
      },
      {
        headerName: "Mapped Gene",
        field: "Mapped gene(s)",
      },
      {
        headerName: "Variant annotation",
        headerClass: "ag-header-cell-center",
        children: [
          {
            field:"Consequence",
            headerName:"Functionl consequence",
            cellRenderer:(params)=>
              params.value.replaceAll("_"," ")
          },
          {
            headerName:"Alpha missense score",
            field:"AlphaMissense",
            cellRenderer:(params)=>
               !params.value.includes("None") ? params.value.replace("_"," ") : ""
          },
          {
            headerName:"SIFT",
            field:"SIFT",
            cellRenderer:(params)=>
               !params.value.includes("None") ? params.value.replace("_"," ") : ""
          },
          {
            headerName:"PolyPhen",
            field:"PolyPhen",
            cellRenderer:(params)=>
               !params.value.includes("None") ? params.value.replace("_"," ") : ""
          },
          {
            headerName:"CADD score",
            field:"CADD"
          },
    
    
          {
            headerName:"Protien family",
            field:"Pfam",
            cellRenderer:(params)=>
           { if(params.value) 
            return (
           
              <a href={params.data.Pfam_url } target="_blank" rel="noopener noreferrer">
                {params.value}
              </a>
            )}
    
          },
        ],

      },
      
      


    ],
    [diseaseAreaFilter]
  );
  const visibleColumns = useMemo(() => {
    if (activeTab === "studies") {
      return gwasColumnDefs.filter((col) =>
        selectedColumnsGWASStudies.includes(col.field)
      );
    } else {
      return associationColumnDefs.filter((col) =>
        selectedAssociationColumns.includes(col.field)
      );
    }
  }, [
    gwasColumnDefs,
    associationColumnDefs,
    selectedColumnsGWASStudies,
    selectedAssociationColumns,
    activeTab,
  ]);

  const handleColumnChange = (columns: string[]) => {
    if (activeTab === "studies") {
      setSelectedColumnsGWASStudies(columns);
    } else {
      setSelectedAssociationColumns(columns);
    }
  };
  const { register, invoke } = useChatStore();
  const payload = {
    diseases: indications,
  };

  const [diseaseData, setDiseaseData] = useState([]);

  useEffect(() => {
    if (activeTab === "studies") {
      setColumns(gwasColumnDefs);
      setDefaultSelectedColumns(selectedColumnsGWASStudies);
    } else {
      setColumns(associationColumnDefs);
      setDefaultSelectedColumns(selectedAssociationColumns);
    }
  }, [
    activeTab,
    associationColumnDefs,
    gwasColumnDefs,
    selectedAssociationColumns,
    selectedColumnsGWASStudies,
  ]);

  const {
    data,
    error,
    isLoading: locusZoomDataLoading,
  } = useQuery(
    ["mondo-data", payload],
    () => fetchData(payload, "/genomics/locus-zoom"),
    {
      enabled: !!indications.length,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );
  useEffect(() => {
    if (data) {
      const locusZoomData = convertTODiseaseArray(data);
      setDiseaseData(locusZoomData);
    }
  }, [data]);
  const queryResults = useQueries(
    diseaseData.map((item) => ({
      queryKey: ["mondo-data", item.mondoId],
      queryFn: async () => {
        const response = await axios.get(
          `${import.meta.env.VITE_API_URI}/api/download/${item.mondoId}.tsv`,
          {
            responseType: "text",
          }
        );
        const parsedData = parseTsvData(response.data);
        console.log("Parsed Data for", item.mondoId, parsedData);
        // Add disease name to each record for better context
        return parsedData.map((record) => ({
          ...record,
          DiseaseArea: item.disease,
          mapped_diseases: record["Mapped Trait"]
            ? record["Mapped Trait"].split(",")
            : [],
        }));
      },
      enabled: !!diseaseData.length && !!item.mondoId,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }))
  );

  const isQueriesLoading = queryResults.some((result) => result.isLoading);
  const hasErrors = queryResults.some((result) => result.error);

  const combinedData = useMemo(() => {
    if (isQueriesLoading || hasErrors) return [];

    return queryResults.reduce((accumulator, result) => {
      if (result.data) {
        return [...accumulator, ...result.data];
      }
      return accumulator;
    }, []);
  }, [queryResults, isQueriesLoading, hasErrors]);

  const {
    data: gwasStudiesData,
    error: gwasStudiesError,
    isLoading,
  } = useQuery(
    ["gwas-studies", payload],
    () => fetchData(payload, "/genomics/gwas-studies"),
    {
      enabled: !!indications.length,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );

  const processedData = useMemo(() => {
    if (gwasStudiesData) {
      const { result } = convertToArray(gwasStudiesData);
      return result;
    }
    return [];
  }, [gwasStudiesData]);

  const rowData = useMemo(() => {
    if (diseaseAreaFilter) {
      return filterByDiseases(
        processedData,
        selectedDiseaseAreas,
        indications,
        "DiseaseArea"
      );
    }
    return processedData;
  }, [processedData, selectedDiseaseAreas, indications, diseaseAreaFilter]);

  const associationsRowData = useMemo(() => {
    if (diseaseAreaFilter) {
      return filterByDiseases(
        combinedData,
        selectedDiseaseAreas,
        indications,
        "DiseaseArea"
      );
    }
    return combinedData;
  }, [combinedData, selectedDiseaseAreas, indications, diseaseAreaFilter]);
  const filterAssociationData = useMemo(() => {
    if (!(selectedDisease.length > 0) && !selectedGene) {
      return associationsRowData;
    }
    console.log("Filtering associations data",associationsRowData,selectedDisease,selectedGene);
   
    let filteredData = associationsRowData;
    if (selectedDisease.length !== 0) {
      filteredData = filteredData?.filter((row) =>
        row.mapped_diseases?.some((d: string) =>
          selectedDisease.some(
            (sel) => d.toLowerCase().trim() === sel.toLowerCase().trim()
          )
        )
      );
    }

    if (selectedGene) {
      filteredData = filteredData.filter((row) => {
        // Split the "Mapped gene(s)" by commas or semicolons and trim whitespace
        const genes = row["Mapped gene(s)"]
          ? row["Mapped gene(s)"].split(/[;,]+/).map((g) => g.trim())
          : [];
        
        // Check if any of the genes exactly matches the selectedGene
        const matchesGene = genes.some((gene) => gene === selectedGene?.trim());
        
        return matchesGene;  // Keep rows that have a gene matching the selectedGene
      });
      
    }
    return filteredData;
  }, [associationsRowData, selectedDisease, selectedGene]);
  useEffect(() => {
    // 1. First, calculate what the *new* accessions list should be.
    let newAccessions = []; // <-- Starts empty every time

    if (selectedGene) {
      // Filter the base data to find all accessions related to the *current* gene
      const geneFilteredData = associationsRowData.filter((row) => {
         const genes = row["Mapped gene(s)"]
           ? row["Mapped gene(s)"].split(/[;,]+/).map((g) => g.trim())
           : [];
         return genes.some((gene) => gene === selectedGene?.trim());
      });

      // Get all accessions from the filtered data
      const accessions = geneFilteredData.map(
        (row) => row["Study Accession"]
      );

      // Get only the unique accessions for *this* gene
      newAccessions = [...new Set(accessions)]; // <-- This is a *new* list, not an appended one.
    }

    // 2. Use the functional update form to *conditionally* set state.
    setSelectedAccession((prevAccessions) => {
      // Sort both arrays to ensure order doesn't matter
      const sortedPrev = [...prevAccessions].sort();
      const sortedNew = [...newAccessions].sort();

      // Check if the new array is *actually different* from the previous one.
      const isSame =
        sortedPrev.length === sortedNew.length &&
        sortedPrev.every((val, index) => val === sortedNew[index]);

      if (isSame) {
        // If they are the same, return the *previous* state reference
        // This prevents the infinite loop.
        return prevAccessions;
      } else {
        // If they are different, return the *new* array.
        // This *replaces* the old [1, 2] with the new [3, 4].
        return newAccessions;
      }
    });
    
  }, [selectedGene, associationsRowData]);
  //  useEffect(() => {
  //     const diseases = Array.from(new Set(rowData.map(item => capitalizeFirstLetter(item["Trait(s)"])))).sort();
  //     setDiseaseFilterOptions(diseases);
  //   }, [rowData]);
  const filteredData = useMemo(() => {
    let filtered = rowData;
    
    if (selectedDisease.length > 0) {
      filtered = filtered.filter((item) =>
        selectedDisease.includes(capitalizeFirstLetter(item["Trait(s)"]))
      );
    }
    
    // This logic is now correct. It will filter *after* the useEffect
    // has successfully set the new accession list (if any).
    if (selectedAccession.length > 0) {
      // console.log("applying accession filter", selectedAccession); // This log is fine
      filtered = filtered.filter((item) =>
        selectedAccession.includes(item["Study accession"])
      );
    } else if (selectedGene) {
      // If a gene is selected but the accession list is *still* empty
      // (e.g., data is loading or no accessions found), show nothing.
      filtered = [];
    }
    
    return filtered;
  }, [rowData, selectedDisease, selectedAccession, selectedGene]);

  useEffect(() => {
    const llmData = preprocessGWASStudiesData(rowData);
    const associationData = preprocessAssociationData(associationsRowData);
    register("gwas", {
      disease: selectedDisease.includes("All")
        ? indications.map((indication) => indication.toLowerCase())
        : selectedDisease,
      data: llmData,
      data1: associationData,
    });
  }, [rowData, selectedDisease, indications, register]);

  const handleLLMCall = () => {
    if (processedData.length === 0) {
      message.warning(
        "This feature requires context to be passed to LLM. As there is no data available, this feature cannot be used"
      );
      return;
    }
    invoke("gwas", { send: false });
  };

  return (
    <div className="my-5" id="gwas-studies">
      <div className="flex gap-2">
        <h2 className="text-xl subHeading font-semibold mb-3 " id="gwasStudies">
          GWAS studies
        </h2>
        <Button
          type="default"
          onClick={handleLLMCall}
          className="w-18 h-8 text-blue-800 text-sm flex items-center"
        >
          <BotIcon width={16} height={16} fill="#d50f67" />
          <span>Ask LLM</span>
        </Button>
      </div>

      {locusZoomDataLoading && <LoadingButton />}
      {(gwasStudiesError || error) && (
        <div>
          <Empty description={`${gwasStudiesError}`} />
        </div>
      )}
      {!isLoading && !gwasStudiesError && gwasStudiesData && (
        <div className="mt-4">
          <div className="flex mb-3">
            <div className="flex gap-4">
              
              {diseaseAreaFilter && (
                <DiseaseFilter
                  allDiseases={indications}
                  selectedDiseases={selectedDiseaseAreas}
                  onChange={setSelectedDiseaseAreas}
                  disabled={isLoading}
                  width={300}
                  labelText={diseaseAreaFilter ? "Disease Area:" : "Disease:"}
                />
              )}
              <div>
              <span className="mt-1 mr-1">Gene: </span>
              
                <Select
                  style={{ width: 300 }}
                  placeholder="Select a Gene"
                  value={selectedGene}
                  onChange={(value) => setSelectedGene(value)}
                  allowClear
                  showSearch
                >
                  {/* <Option value="">Select Gene (Coming soon)</Option> */}
                    {Array.from(
                    new Set([
                      ...(target ? [target] : []), // Add target if it exists
                      ...associationsRowData.flatMap(
                      (item) => (item["Mapped gene(s)"] || "").split(/[,;]/) // Split by comma or semicolon
                      )
                    ])
                    )
                    .filter((gene) => gene.trim() !== "") // Remove any empty strings
                    .sort()
                    .map((gene) => (
                      <Option key={gene} value={gene}>
                      {gene}
                      </Option>
                    ))}
                </Select>
              
              </div>
              {/* <DiseaseFilter
            allDiseases={diseaseFilterOptions}
            selectedDiseases={selectedDisease}
            onChange={setSelectedDisease}
            disabled={isLoading}
            width={300}
            labelText="Disease:"
          /> */}
            </div>
          </div>
          <div className="flex justify-between my-3">
            <div>
              <span>Available Data: </span>
              <ConfigProvider
                theme={{
                  components: {
                    Segmented: {
                      itemSelectedBg: "#1890ff",
                      itemSelectedColor: "white",
                    },
                  },
                }}
              >
                <Segmented
                  options={[
                    { label: "Associations", value: "association" },
                    { label: "Studies", value: "studies" },
                  ]}
                  value={activeTab}
                  onChange={(value) => setActiveTab(value)}
                />
              </ConfigProvider>
            </div>
            <div className="flex gap-2">
              <ColumnSelector
                allColumns={columns}
                defaultSelectedColumns={defaultSelectedColumns}
                onChange={handleColumnChange}
              />
              <ExportButton
                indications={indications}
                endpoint="/genomics/gwas-studies"
                fileName="GWAS-Studies"
              />
            </div>
          </div>

          {activeTab === "studies" && (
            <div>
              <Table rowData={filteredData} columnDefs={visibleColumns} />
            </div>
          )}

          {activeTab === "association" && (
            <div>
              <Table
                columnDefs={visibleColumns}
                rowData={filterAssociationData}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AssociatePlot;
