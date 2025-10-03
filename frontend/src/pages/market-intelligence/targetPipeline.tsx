import { useQuery } from "react-query";
import { fetchData } from "../../utils/fetchData";
import { useEffect, useState, useMemo } from "react";
import { Empty, Button, Select,message } from "antd";
import Patent from "./patent";
import ExportButton from "../../components/exportButton";
import he from "he";
import ApprovedDrug from "./targetApprovedDrug";
import { capitalizeFirstLetter } from "../../utils/helper";
import LoadingButton from "../../components/loading";
import { useChatStore } from "chatbot-component";
import BotIcon from "../../assets/bot.svg?react";
import { preprocessTargetData } from "../../utils/llmUtils";
import ColumnSelector from "../../components/columnFilter";
import parse from "html-react-parser";
import Table from "../../components/table";
const { Option } = Select;

const CompetitiveLandscape = ({target,indications}) => {
  const [selectedDisease, setSelectedDisease] = useState(indications);
  const [selectedModality, setSelectedModality] = useState('All');

  const [selectedColumns, setSelectedColumns] = useState([
    "Disease",
    "Source URLs",
    "WhyStopped",
    "OutcomeStatus",
    "Drug",
    "Type",
    "Phase",
    "Status",
    "Sponsor",
    "Mechanism of Action",
  ]);

  // const [selectedDisease, setSelectedDisease] = useState('All');
  // const [selectedModality, setSelectedModality] = useState('Antibody');
  // const [rowData, setRowData] = useState([]);

  const { register, invoke } = useChatStore();



  const payload = {
    target:target?.toLowerCase(),
    diseases: [
      "no-disease"
    ],
  };

  const {
    data: targetData,
    error: targetError,
    isLoading: targetDataLoading,
    isFetching: targetDataFetching,
    isFetched: targetDataFetched,
  } = useQuery(
    ["marketIntelligenceTarget", payload],
    () => fetchData(payload, "/market-intelligence/target-pipeline-new/"),
    {
      enabled: !!target ,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
      keepPreviousData: true,
    }
  );
  const columnDefs = useMemo(() => [
    {
      field: "NctIdTitleMapping",
      headerName: "Trial summary",
      flex: 8,
      minWidth: 300,
      valueGetter: (params) => {
        if (params.data.NctIdTitleMapping) {
          return Object.entries(params.data.NctIdTitleMapping)
            .map(
              ([key, value]) =>
                `<div><span className="font-semibold">${key}:</span> ${
                  value ? value : "No official title available"
                }</div>`
            )
            .join("\n\n");
        }
        return "";
      },
      cellStyle: { whiteSpace: "pre-wrap" },
      filter: true,
      cellRenderer: (params) => {
        return parse(params.value);
      },
    },

    {
      field: "Disease",
      cellRenderer: (params) => capitalizeFirstLetter(params.value),
      flex: 2,
    },
    {
      field: "Source URLs",
      headerName: "Trial Id",
      flex: 2,
      cellRenderer: (params) => {
        if (params.value)
          return params.value.map((value, index) => (
            <a key={index} className="mr-2" href={value} target="_blank">
              {value.replace("https://clinicaltrials.gov/study/", "")}
              {params.value.length - 1 !== index ? "," : ""}
            </a>
          ));
        else return "No data available";
      },
    },
    {
      field: "WhyStopped",
      headerName: "Outcome reason",
      flex: 3,
      cellStyle: { whiteSpace: "normal", lineHeight: "20px" },
      cellRenderer: (params) => {
        if (params.data.Status == "Completed" && params.data.PMIDs.length > 0)
          return params.data.PMIDs.map((pmid, index) => (
            <a
              key={index}
              className="mr-2"
              href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}`}
              target="_blank"
            >
              {pmid}
              {params.data.PMIDs.length - 1 !== index ? "," : ""}
            </a>
          ));
        else return he.decode(params.value);
      },
      valueGetter: (params) => {
        if (params.data.Status == "Completed" && params.data.PMIDs.length > 0)
          return params.data.PMIDs;
        else return params.data.WhyStopped;
      },
    },
    {
      field: "OutcomeStatus",
      flex: 2,
      headerName: "Trial outcome",
      cellRenderer: (params) => {
        return capitalizeFirstLetter(params.value);
      },
    },
    {
      field: "Drug",
      flex: 2,
    },
    { field: "Type", flex: 2, headerName: "Modality" },
    { field: "Phase" },

    { field: "Status", flex: 2 },

    { field: "Sponsor", flex: 2 },
    { field: "Mechanism of Action", flex: 3 },
  ], []);
  const processedData = useMemo(() => {
    if (targetData && Object.keys(targetData).length > 0) {
      console.log("targetData", targetData);
      return targetData.target_pipeline.target_pipeline;
    }
    return [];
  }, [targetData]);
  useEffect(() => {
    setSelectedDisease(indications);
  }, [indications]);
  const filteredData = useMemo(() => {
    const diseaseFiltered = selectedDisease.length===0
      ? processedData
      : processedData.filter((row) =>
          selectedDisease.some(
            (indication) =>
              indication.toLowerCase() === row.Disease.toLowerCase()
          )
        );
        return selectedModality === 'All'
      ? diseaseFiltered
      : diseaseFiltered.filter((item) => item.Type === selectedModality);
  }, [processedData, selectedDisease,selectedModality]);

  useEffect(() => {
    if (targetData?.target_pipeline?.target_pipeline) {
      const llmData = preprocessTargetData(targetData.target_pipeline.target_pipeline);
      // console.log(llmData);
      register("pipeline_target", {
        target: target,
        diseases: indications?.map((item) => item.toLowerCase()),
        data: llmData,
      });
    }
  }, [targetData]);

  const handleLLMCall = () => {
    if(processedData.length===0){
      message.warning("This feature requires context to be passed to LLM. As there is no data available, this feature cannot be used");
      return;
    }
    invoke("pipeline_target", { send: false });
  };
  const handleModalityChange = (value) => setSelectedModality(value);

  const handleDiseaseChange = (value: string[]) => {
    console.log("value",value)
    if (value.includes("All")) {
      // If "All" is selected, select all diseases but don't include "All" in display
      setSelectedDisease(["All"]);
      console.log("selectedDisease", selectedDisease);
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
  const visibleColumns = useMemo(() => {
    return columnDefs.filter((col) => selectedColumns.includes(col.field));
  }, [columnDefs, selectedColumns]);

  const handleColumnChange = (columns: string[]) => {
    setSelectedColumns(columns);
  };

  return (
    <div className="mt-8">
      <section id="approvedDrug">
        <ApprovedDrug
          approvedDrugData={targetData}
          loading={targetDataLoading}
          error={targetError}
          indications={indications}
          isFetchingData={targetDataFetching}
          target={target}
        />
      </section>
      <section id="pipeline-by-target" className="px-[5vw]">
        <div className="flex space-x-5 items-center">
          <h1 className="text-3xl font-semibold">Therapeutic pipeline </h1>
          <Button
            type="default" // This will give it a simple outline
            onClick={handleLLMCall}
            className="w-18 h-8 text-blue-800 text-sm flex items-center"
          >
            <BotIcon width={16} height={16} fill="#d50f67" />
            <span>Ask LLM</span>
          </Button>
        </div>
        <p className="mt-2  font-medium">
        The table offers a comprehensive overview of drug candidates, categorized by indication, development status, and mechanism of action, based on data from ongoing and completed clinical trials. It supports scientists in validating drug targets across modalities and indications.
        </p>
      
        {targetError && (
          // Error div with same height as AgGrid
          <div className="ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center">
            <Empty description={String(targetError)} />
          </div>
        )}
        {targetDataLoading && <LoadingButton />}

        {!targetDataLoading &&
          !targetError &&
          targetData &&
          targetDataFetched && (
            <div>
              { processedData?.length>0 &&<div className="flex justify-between my-2">
                <div className="flex gap-2">
                  <div>
                    <span className="mt-1 mr-1">Disease: </span>
                    <Select
                      style={{ width: 300 }}
                      onChange={handleDiseaseChange}
                      value={selectedDisease}
                      mode="multiple"
                      maxTagCount="responsive"
                      allowClear={true}
                      placeholder="Select diseases"
                      // disabled={isLoading}
                    >
                      
                      {targetData?.available_diseases.map((indication) => (
                        indication!="all" &&
                        <Option key={indication} value={capitalizeFirstLetter(indication.replace(/_/g, " "))}>
                          {capitalizeFirstLetter(indication.replace(/_/g, " "))}
                        </Option>
                      ))}
                    </Select>
                  </div>
                  <div>
                  <span className='mt-1 mr-1'>Modality: </span>
                  <Select
                    style={{ width: 300 }}
                    onChange={handleModalityChange}
                    value={selectedModality}
                    // disabled={isLoading}
                  >
                    <Option key='All' value='All'>
                      All
                    </Option>
                    {[...new Set(processedData.map((item) => item.Type))].map(
                      (type: string) => (
                        <Option key={type} value={type}>
                          {type}
                        </Option>
                      )
                    )}
                  </Select>
                </div>
                </div>
                <div className="flex gap-2">
                 {filteredData.length>0 && <ColumnSelector
                    allColumns={columnDefs}
                    defaultSelectedColumns={selectedColumns}
                    onChange={handleColumnChange}
                  />}
                  <ExportButton
                    indications={[""]}
                    target={target}
                    disabled={targetDataLoading || processedData.length === 0}
                    fileName={"Target-Pipeline"}
                    endpoint={"/market-intelligence/target-pipeline-all/"}
                  />
                </div>
              </div>}
              <div className="">
                <Table
                  columnDefs={visibleColumns}
                  rowData={filteredData}
                 
                />
                {
                  filteredData?.length>0&&
                  <p>
                  * The failed entries for the targets include trials that were
                  withdrawn or terminated due to unmet endpoints, financial constraints,
                  or other factors. For detailed explanations, please refer to the
                  respective trial ID from the "Therapeutic pipeline" table.
                </p>
                }
              </div>
            </div>
          )}
        {!targetData &&
          !targetDataLoading &&
          !targetError &&
          targetDataFetched && (
            <div className="ag-theme-quartz mt-4 h-[280px] flex items-center justify-center">
              <Empty description="No data available" />
            </div>
          )}
      </section>

      {/* <section id="kol" className="mt-12 min-h-[80vh]   py-20 px-[5vw]">
        <KOL indications={indications} />
      </section> */}
      <Patent target={target} indications={indications} />
    </div>
  );
};

export default CompetitiveLandscape;