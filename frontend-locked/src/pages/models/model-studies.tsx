import React, { useState, useMemo, useEffect } from "react";
import { Tooltip } from "antd";
import parse from "html-react-parser";
import { fetchData } from "../../utils/fetchData";
import { useQuery } from "react-query";
import { capitalizeFirstLetter, convertDiseaseObjectToArray } from "../../utils/helper";
import { filterByDiseases } from "../../utils/filterDisease";
import DataTableWrapper from "../../components/dataTableWrapper";
import DiseaseFilter from "../../components/diseaseFilter";
import CustomHeader from "../../components/customHeader";
interface ModelStudiesProps {
  indications: string[];
  diseaseAreaFilter: boolean;
}

const ModelStudies: React.FC<ModelStudiesProps> = ({ indications,diseaseAreaFilter }) => {
  const [diseaseFilterOptions, setDiseaseFilterOptions] = useState<string[]>([]);
  const [selectedDiseaseAreas, setSelectedDiseaseAreas] = useState(indications);
  const [selectedDiseases, setSelectedDiseases] = useState<string[]>([]);
  
  useEffect(() => {
    if(!diseaseAreaFilter)
    setSelectedDiseases(indications);
  }, [diseaseAreaFilter, indications]);
  // Define table columns and their properties

  const selectedColumns = [
    "Model",
    "Gene",
    "Species",
    "Disease",
    "References",
  ];
  const columnDefs = useMemo(
    () => [
      {
        field: "Disease",
        headerName: "Disease",
        valueGetter: (params) => {
          return params.data.Disease;
        },
      },
      {
        field: "Species",
        headerName: "Species",
        valueGetter: (params) => {
          return params.data.Species;
        },
        flex: 1,
        cellRenderer: (params) => {
          return <i>{params.value}</i>;
        },
      },
      {
        field: "Gene",
        flex: 3,
        headerName: "Gene perturbed",
        

        valueGetter: (params) => {
          return params.data.Gene;
        },
      },
      {
        field: "Model",
        flex: 3,
        headerName: "Model",
        valueGetter: (params) => params.data.Model,
        cellRenderer: (params) => (
          <Tooltip title="Click to view phenotypes">
            <a
              href={params.data.SourceURL}
              target="_blank"
              rel="noopener noreferrer"
            >
              {parse(params.value)}
            </a>
          </Tooltip>
        ),
      },
      

    

      {
        field: "Association",
        flex: 1,
        headerName: "Association",
        headerComponent:CustomHeader,
        headerComponentParams: { 
          headerName: "Association",
          title:(<ul>
            <li><strong>Is model of</strong> – Model reproduces phenotypes consistent with the human disease.</li>
            <li><strong>Does not model</strong> – Model was evaluated but did not reproduce disease phenotypes.</li>
            <li><strong>Is implicated in</strong> – A variant of the gene is shown to function in causing or modifying a human disease or model state.</li>
            <li><strong>A marker of</strong> – A biological molecule found in blood, other body fluids, or tissues that is a sign of the disease.</li>
          </ul>
          )
         },
        // valueGetter: (params) => {
        //   return params.data.Association;
        // },
        valueGetter: (params) => {
          const associationValue = params.data.Association;
          const type = associationValue.toLowerCase();
          
          if (associationValue == "is_not_model_of") return "does Not model";

          if (type === "is_not_model_of") {
            return "does not model";
          }

          const words = type
            ?.replaceAll("_", " ")
            .split(/(?:^| )not(?: |$)/, 2);
          
          let result = words?.[0] || "";
          if (words?.length > 1) {
            result += " not " + words[1];
          }
          
          return result;
        },
            },
           
      {
        field: "References",
        flex: 1.3,
        headerName: "Reference (PMID)",
        cellRenderer: (params) =>
          params.value.map((value, index) => (
            <a
              key={index}
              className="mr-2"
              href={`https://pubmed.ncbi.nlm.nih.gov/${value}`}
              target="_blank"
            >
              {value}
              {params.value.length - 1 !== index ? "," : ""}
            </a>
          )),
      },
    ],
    []
  );

  const payload = {
    diseases: indications,
  };

  const apiEndpoint = "/evidence/mouse-studies/";

  const { data, isLoading, isError, isFetching } = useQuery(
    ["mouseStudies", payload],
    () => fetchData(payload, apiEndpoint),
    {
      enabled: !!indications.length,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,

      // keepPreviousData: true, // Retain previous data while fetching
    }
  );

  useEffect(() => {
    if (indications.length > 0) {
      setSelectedDiseaseAreas(indications);
    }
  }, [indications]);

  // Memoized processed data to prevent unnecessary re-renders
  const processedData = useMemo(() => {
    if (data) {
      return convertDiseaseObjectToArray(data, "mouse_studies");
    }
    return [];
  }, [data]);

  const dataFilteredByArea = useMemo(() => {
    if (diseaseAreaFilter) {
      return filterByDiseases(processedData, selectedDiseaseAreas, indications,"DiseaseArea");
    }
    return processedData;
  }, [processedData, selectedDiseaseAreas, indications, diseaseAreaFilter]);

  useEffect(() => {
    const diseases = Array.from(new Set(dataFilteredByArea.map(item => capitalizeFirstLetter(item.Disease)))).sort();
    setDiseaseFilterOptions(diseases);
  }, [dataFilteredByArea]);

  const filteredData = useMemo(() => {
    if (selectedDiseases.length > 0) {
      
      return dataFilteredByArea.filter(item => 
      selectedDiseases.includes(capitalizeFirstLetter(item.Disease))
      );
    }
    return dataFilteredByArea;
  }, [dataFilteredByArea, selectedDiseases]);


  // Determine if we should show loading
  const showLoading = isLoading || isFetching;

  return (
    <section id="model-studies" className="mt-8 px-[5vw]">
      <div className="flex items-center gap-x-2">
        <h1 className="text-3xl font-semibold">Perturbed Animal Models</h1>
      </div>

      <p className="mt-2  font-medium">
      This section lists genetically perturbed model organisms with disease-relevant phenotypes, helping researchers identify suitable animal models to study target perturbations and their impact on disease mechanisms, target validation, and drug development.
        <br />
      </p>
      {!showLoading && (
        <div className="text-base">
          <span className="font-bold">Summary: </span>
          There are <span className="text-sky-800">
            {processedData.length}
          </span>{" "}
          animal models available.
        </div>
      )}

      <DataTableWrapper
        isLoading={showLoading}
        error={isError}
        data={processedData}
        filterData={filteredData}
        allColumns={columnDefs}
        defaultColumns={selectedColumns}
        exportOptions={{
          indications,
          fileName: "Animal-Models",
          endpoint: "/evidence/mouse-studies/",
        }}
        filterComponent={
          <>
          <div className="flex gap-x-4">
        {  diseaseAreaFilter &&
          <DiseaseFilter
          allDiseases={indications}
          selectedDiseases={selectedDiseaseAreas}
          onChange={setSelectedDiseaseAreas}
          disabled={showLoading}
          width={300}
          labelText="Disease Area:"
        />}
          <DiseaseFilter
            allDiseases={diseaseFilterOptions}
            selectedDiseases={selectedDiseases}
            onChange={setSelectedDiseases}
            disabled={showLoading}
            width={300}
            labelText="Disease:"
            showAllOption={false}
          />
          </div>
          </>
        }
      />
    </section>
  );
};

export default ModelStudies;
