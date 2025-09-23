import { useEffect, useState, useMemo } from "react";
import { useQuery, useQueries } from "react-query";
import { Empty, Select, Button, Segmented, ConfigProvider, message } from "antd";
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
          disease: capitalizeFirstLetter(disease), // Add the disease key
        });
      });
    } else {
      diseaseWithoutEFOID.push(disease);
    }
  });

  return { result, diseaseWithoutEFOID };
}
const AssociatePlot = ({ indications }) => {
  const [selectedDisease, setSelectedDisease] = useState(indications);
  const [activeTab, setActiveTab] = useState("studies");
  const [columns, setColumns] = useState([]);
  const [defaultSelectedColumns, setDefaultSelectedColumns] = useState([]);
  const [selectedColumnsGWASStudies, setSelectedColumnsGWASStudies] = useState([
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
  const [selectedAssociationColumns, setSelectedAssociationColumns] = useState([
    "diseaseName",
    "Study Accession",
    "Variant and Risk Allele",
    "pvalue",
    "RAF",
    "OR or BETA",
    "CI",
    "Mapped gene(s)",
  ]);
  const gwasColumnDefs = useMemo(()=>[
    {
      headerName: "Disease",
      field: "disease",
    },
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
  ],[]);
  const associationColumnDefs = useMemo(() => [
    {
      headerName: "Disease",
      field: "diseaseName",
    },
    {
      headerName: "Study Accession",
      field: "Study Accession",
    },
    {
      headerName: "Variant and Risk Allele",
      field: "Variant and Risk Allele",
    },
    {
      headerName: "p-value",
      field: "pvalue",
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
  ], []);
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
    setSelectedDisease(indications);
  }, [indications]);
  useEffect(() => {
    if (activeTab === "studies") {
      setColumns(gwasColumnDefs);
      setDefaultSelectedColumns(selectedColumnsGWASStudies);
    } else {
      setColumns(associationColumnDefs);
      setDefaultSelectedColumns(selectedAssociationColumns);
    }
  }, [activeTab]);

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

        // Add disease name to each record for better context
        return parsedData.map((record) => ({
          ...record,
          diseaseName: item.disease,
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
    if (processedData.length > 0) {
      // If all diseases are selected (length matches total indications)
      return selectedDisease.length === indications.length
        ? processedData
        : processedData.filter((row) =>
            selectedDisease.some(
              (indication) =>
                indication?.toLowerCase() === row.disease?.toLowerCase()
            )
          );
    }
    return [];
  }, [processedData, selectedDisease, indications]);

  const associationsRowData = useMemo(() => {
    if (combinedData.length > 0) {
      // If all diseases are selected (length matches total indications)
      return selectedDisease.length === indications.length
        ? combinedData
        : combinedData.filter((row) =>
            selectedDisease.some(
              (indication) =>
                indication?.toLowerCase() === row.diseaseName?.toLowerCase()
            )
          );
    }
    return [];
  }, [combinedData, selectedDisease, indications]);
  console.log("associationsRowData", associationsRowData);
  const handleDiseaseChange = (value) => {
    if (value.includes("All")) {
      // If "All" is selected, select all diseases but don't include "All" in display
      setSelectedDisease(indications);
    } else if (
      selectedDisease.length === indications.length &&
      value.length < indications.length
    ) {
      // If coming from "all selected" state and deselecting, just use the new selection
      setSelectedDisease(value);
    } else {
      // Normal selection behavior
      setSelectedDisease(value);
    }
  };

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
    if(processedData.length===0){
      message.warning("This feature requires context to be passed to LLM. As there is no data available, this feature cannot be used");
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
            <div>
              <span className="mt-10 mr-1">Disease: </span>
              <span>
                <Select
                  style={{ width: 500 }}
                  mode="multiple"
                  maxTagCount="responsive"
                  onChange={handleDiseaseChange}
                  value={selectedDisease}
                  disabled={isLoading}
                  showSearch={false}
                >
                  <Option value="All">All</Option>
                  {indications.map((indication) => (
                    <Option key={indication} value={indication}>
                      {indication}
                    </Option>
                  ))}
                </Select>
              </span>
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
                    { label: "Studies", value: "studies" },
                    { label: "Associations", value: "association" },
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
              <Table rowData={rowData} columnDefs={visibleColumns} />
            </div>
          )}

          {activeTab === "association" && (
            <div>
              <Table
                columnDefs={visibleColumns}
                rowData={associationsRowData}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AssociatePlot;