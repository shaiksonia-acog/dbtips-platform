import { useQuery } from "react-query";
import { fetchData } from "../../utils/fetchData";
import { useEffect, useState, useMemo } from "react";
import { Empty, Button, message } from "antd";
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
import CustomHeader from "../../components/customHeader";
// import parse from "html-react-parser";
import Table from "../../components/table";
import DiseaseFilter from "../../components/diseaseFilter";

const CompetitiveLandscape = ({ target, indications, diseaseAreaFilter }) => {
  const [selectedDisease, setSelectedDisease] = useState([]);
  // const [selectedModality, setSelectedModality] = useState("All");
  const [selectedDiseaseAreas, setSelectedDiseaseAreas] = useState(indications);
  const [diseaseOptions, setDiseaseOptions] = useState([]);

  const [selectedColumns, setSelectedColumns] = useState([
    "diseaseArea",
    "Disease",
    "Source URLs",
    "Modality",
    "WhyStopped",
    "OutcomeStatus",
    "Drug",
    "Type",
    "Phase",
    "Status",
    "Sponsor",
    "Mechanism of Action",
  ]);
  const [approvedDrugData, setApprovedDrugData] = useState([]);

  const { register, invoke } = useChatStore();

  const payload = {
    target: target?.toLowerCase(),
    diseases: indications.length > 0 ? indications : ["no-disease"],
  };
  const { data: targetData,
    error: targetError,
    isLoading: targetDataLoading,
    isFetching: targetDataFetching,
    isFetched: targetDataFetched, } = useQuery(
      ["targetPipeline", payload],
      () =>
        fetchData(
          payload, `/market-intelligence/target-pipeline-new/`
        ),
      {
        enabled: !!target,
        staleTime: 5 * 60 * 1000, // 5 minutes
        cacheTime: 15 * 60 * 1000, // 15 minutes
      }
    );

  // For testing with local JSON data
  //


  const columnDefs = useMemo(
    () => [
      {
        field: "OfficialTitle",
        headerName: "Trial summary",
        flex: 8,
        minWidth: 300,
       
        
      },
      ...(diseaseAreaFilter
        ? [
          {
            field: "diseaseArea",
            headerName: "Disease Area",
            flex: 2,
          },
        ]
        : []),
      {
        field: "Disease",
        cellRenderer: (params) => capitalizeFirstLetter(params.value),
        flex: 2,
      },
       {
        field: "Drug",
        flex: 2,
        cellRenderer: (params) => params.value.toUpperCase(),
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
          else return "";
        },
      },
      { field: "Phase" },

      {
        field: "OutcomeStatus",
        flex: 2,
        headerName: "Trial outcome",
        headerComponent: CustomHeader,
        headerComponentParams: {
          displayName: "Trial outcome",
          title:
            (
              <div>
                <ul style={{ margin: '8px 2px' }}>
                  <li><strong>Success</strong> – The trial successfully met its endpoint.</li>
                  <li><strong>Failure</strong> – The trial did not meet its endpoint.</li>
                  <li><strong>Indeterminate</strong> – The outcome is unclear or lacks conclusive evidence to classify as success or failure.</li>
                  <li><strong>Not known</strong> – No information available.</li>
                </ul>
              </div>
            ),
        },
        cellRenderer: (params) => {
          return capitalizeFirstLetter(params.value);
        },
      },
      {
        field: "WhyStopped",
        headerComponent: CustomHeader,
        headerComponentParams: {
          displayName: "Source/Reference",
          title:
            "Indicates the reference used to determine the trial’s outcome status.",
        },
        flex: 3,
        cellStyle: { whiteSpace: "normal", lineHeight: "20px" },
        cellRenderer: (params) => {
          // Display both PMIDs and WhyStopped

          const pmidLinks = params.data?.PMIDs?.map((pmid, index) => (
            <a
              key={index}
              className='mr-2'
              href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}`}
              target='_blank'
            >
              {pmid}
              {params.data.PMIDs.length - 1 !== index ? ',' : ''}
            </a>
          ));

          // Show the WhyStopped value
          const whyStopped = params.data.WhyStopped ? he.decode(params.data.WhyStopped) : "";

          return (
            <div>
              <div className='mb-2'>{`${params.data.PMIDs?.length > 0 ? "PMID: " : ""}`} {pmidLinks}</div>
              <div>{whyStopped}</div>
            </div>
          );
        },
        valueGetter: (params) => {
          // Return both PMIDs and WhyStopped as separate values
          return {
            pmids: params.data.PMIDs,
            whyStopped: params.data.WhyStopped
          };
        },
      },
      
     
      { field: "Modality", flex: 2, },
      { field: "Sponsor", flex: 2 },
      { field: "Mechanism of Action", flex: 3 },
      { field: "Status", flex: 2 },
    ],
    [diseaseAreaFilter]
  );

  // Process the data from JSON
  const processedData = useMemo(() => {
    if (targetData && Object.keys(targetData).length > 0) {
      return targetData.target_pipeline;
    }
    return [];
  }, [targetData]);

  // Get disease area options from disease_tree_numbers keys
  const diseaseAreaOptions = useMemo(() => indications, [indications]);
  const getMatchingIndications = (row, indications, mapping) => {
    const itemTreeNumbers = row.disease_tree_numbers || [];
    return indications.filter((area) => {
      const catTreeNumbers = mapping[area] || [];
      return itemTreeNumbers.some((itemTreeNum) =>
        catTreeNumbers.some((catTreeNum) => itemTreeNum.startsWith(catTreeNum))
      );
    });
  };

  useEffect(() => {
    if (!indications?.length) {
      setApprovedDrugData(processedData);
      return;
    }

    const mapping = targetData?.disease_tree_numbers || {};
    const approved = processedData.flatMap((row) => {
      const matches = getMatchingIndications(row, indications, mapping);
      return matches.map((indication) => ({ ...row, diseaseArea: indication }));
    });

    setApprovedDrugData(approved);
  }, [indications, processedData, targetData]);


  // Initialize selected disease areas with all options
  useEffect(() => {
    if (!diseaseAreaFilter) {
      setSelectedDisease(indications)
    }

    setSelectedDiseaseAreas(diseaseAreaOptions);
  }, [diseaseAreaOptions, diseaseAreaFilter, indications]);

  // Filter by disease area (multiple selection)
  const areaFiltered = useMemo(() => {
    if (!diseaseAreaFilter && indications.length == 0) return processedData;
    if (!selectedDiseaseAreas.length) return [];

    const mapping = targetData?.disease_tree_numbers || {};

    return processedData.flatMap((row) => {
      const matchingIndications = selectedDiseaseAreas.filter((area) => {
        const areaTreeNumbers = mapping[area] || [];
        return (row.disease_tree_numbers || []).some((itemNum) =>
          areaTreeNumbers.some((selNum) => itemNum.startsWith(selNum))
        );
      });

      return matchingIndications.map((indication) => ({
        ...row,
        diseaseArea: indication
      }));
    });
  }, [diseaseAreaFilter, indications.length, processedData, selectedDiseaseAreas, targetData?.disease_tree_numbers]);

  // Get disease options grouped by disease area
  useEffect(() => {
    const diseases = areaFiltered.map((i) => i.Disease).filter(Boolean);
    const uniqueDiseases = [...new Set(diseases)].sort();
    if (!diseaseAreaFilter)
      setDiseaseOptions([...uniqueDiseases, ...indications].sort());
    else setDiseaseOptions(uniqueDiseases);
  }, [areaFiltered, indications, diseaseAreaFilter]);

  // Reset selected diseases when disease options change
  // useEffect(() => {
  //   setSelectedDisease((prev) =>
  //     prev.filter((d) => diseaseOptions.includes(d))
  //   );
  // }, [diseaseOptions]);

  // Filter by disease and modality
  const filteredData = useMemo(() => {
    const diseaseFiltered =
      selectedDisease.length === 0
        ? areaFiltered
        : areaFiltered.filter((row) =>
          selectedDisease.some(
            (disease) => disease.toLowerCase() === row.Disease.toLowerCase()
          )
        );

    // return selectedModality === "All"
    //   ? diseaseFiltered
    //   : diseaseFiltered.filter((item) => item.Modality === selectedModality);
    return diseaseFiltered;
  }, [areaFiltered, selectedDisease]);

  // Register data with LLM
  useEffect(() => {
    if (targetData?.target_pipeline) {
      const llmData = preprocessTargetData(approvedDrugData);
      register("pipeline_target", {
        target: target,
        diseases: Object.keys(targetData.disease_tree_numbers || {}),
        data: llmData,
      });
    }
  }, [approvedDrugData, targetData, target, register]);

  const handleLLMCall = () => {
    if (processedData.length === 0) {
      message.warning(
        "This feature requires context to be passed to LLM. As there is no data available, this feature cannot be used"
      );
      return;
    }
    invoke("pipeline_target", { send: false });
  };

  // const handleModalityChange = (value) => setSelectedModality(value);


  const visibleColumns = useMemo(() => {
    return columnDefs.filter((col) => selectedColumns.includes(col.field));
  }, [columnDefs, selectedColumns]);

  const handleColumnChange = (columns) => {
    setSelectedColumns(columns);
  };



  return (
    <div className="mt-8">
      <section id="approvedDrug">
        <ApprovedDrug
          approvedDrugData={approvedDrugData}
          loading={targetDataLoading}
          error={targetError}
          indications={indications}
          isFetchingData={targetDataFetching}
          target={target}
          diseaseAreaFilter={diseaseAreaFilter}
        />
      </section>
      <section id="pipeline-by-target" className="px-[5vw]">
        <div className="flex space-x-5 items-center">
          <h1 className="text-3xl font-semibold">Therapeutic pipeline </h1>
          <Button
            type="default"
            onClick={handleLLMCall}
            className="w-18 h-8 text-blue-800 text-sm flex items-center"
          >
            <BotIcon width={16} height={16} fill="#d50f67" />
            <span>Ask LLM</span>
          </Button>
        </div>
        <p className="mt-2 font-medium">
        The table provides a comprehensive overview of drug candidates across research, pre-clinical, and clinical phases, categorized by indication, development status, and mechanism of action. It enables scientists to explore and validate drug targets across modalities and disease areas, based on data across stages from discovery to preclinical studies to ongoing and completed clinical trials.
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
              {processedData?.length > 0 && (
                <div className="flex justify-between my-2">
                  <div className="flex gap-2">
                    {diseaseAreaFilter && (
                      <div>
                        <DiseaseFilter
                          allDiseases={indications}
                          selectedDiseases={selectedDiseaseAreas}
                          onChange={setSelectedDiseaseAreas}
                          labelText="Disease area:"
                          width={300}

                        />
                      </div>
                    )}

                    <div>
                      <DiseaseFilter
                        allDiseases={diseaseOptions}
                        selectedDiseases={selectedDisease}
                        onChange={setSelectedDisease}
                        labelText="Disease:"
                        width={300}
                        placeholder="Select diseases"
                        showAllOption={false}
                      />
                    </div>
                    {/*                   
                  <div>
                    <span className="mt-1 mr-1">Modality: </span>
                    <Select
                      style={{ width: 300 }}
                      onChange={handleModalityChange}
                      value={selectedModality}
                    >
                      <Option key="All" value="All">
                        All
                      </Option>
                      {[
                        ...new Set(processedData.map((item) => item.Modality)),
                      ].map((type) => (
                        <Option key={(type as string)} value={type}>
                          {(type as string)}
                        </Option>
                      ))}
                    </Select>
                  </div> */}
                  </div>
                  <div className="flex gap-2">
                    {filteredData.length > 0 && (
                      <ColumnSelector
                        allColumns={columnDefs}
                        defaultSelectedColumns={selectedColumns}
                        onChange={handleColumnChange}
                      />
                    )}
                    <ExportButton
                      indications={indications}
                      target={target}
                      disabled={targetDataLoading || processedData.length === 0}
                      fileName={"Target-Pipeline"}
                      endpoint={"/market-intelligence/target-pipeline-new/"}
                    />
                  </div>
                </div>
              )}
              <div>
                <Table columnDefs={visibleColumns} rowData={filteredData} />

                {filteredData?.length > 0 && (
                  <p>
                    * The failed entries for the targets include trials that were
                    withdrawn or terminated due to unmet endpoints, financial
                    constraints, or other factors. For detailed explanations,
                    please refer to the respective trial ID from the "Therapeutic
                    pipeline" table.
                  </p>
                )}
              </div>
            </div>
          )}
        {!targetData &&
          !targetDataLoading &&
          !targetError &&
          targetDataFetched && (
            <div className="mt-4 h-[280px] flex items-center justify-center">
              <Empty description="No data available" />
            </div>
          )}
      </section>

      {/* <section id="kol" className="mt-12 min-h-[80vh] py-20 px-[5vw]">
        <KOL indications={indications} />
      </section> */}
      <Patent target={target} indications={indications} diseaseAreaFilter={diseaseAreaFilter} />
    </div>
  );
};

export default CompetitiveLandscape;