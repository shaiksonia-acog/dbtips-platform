import { useEffect, useMemo, useState } from "react";
// import data from "./ppm.json"
// import { AgGridReact } from "ag-grid-react";
import parse from "html-react-parser";
import ColumnSelector from "../../components/columnFilter";
import Table from "../../components/table";
import { filterByDiseases } from "../../utils/filterDisease";
import DiseaseFilter from "../../components/diseaseFilter";
import { capitalizeFirstLetter } from "../../utils/helper";
function renderPgsEffectSizes(pgs_effect_sizes) {
  if (!Array.isArray(pgs_effect_sizes) || pgs_effect_sizes.length === 0) {
    return "";
  }

  const effect = pgs_effect_sizes[0];
  const hasCI =
    effect.ci_lower !== undefined &&
    effect.ci_lower !== null &&
    effect.ci_upper !== undefined &&
    effect.ci_upper !== null;

  const ciText = hasCI ? ` [${effect.ci_lower} - ${effect.ci_upper}]` : "";

  return `
      <div >
     <span title="${effect.name_long}" style="font-weight:600; cursor:pointer;">
        ${effect.name_short}
      </span>
      <span>: ${effect.estimate}${ciText}</span>
    </div>
    `;
}

const PPM = ({ data, diseaseAreaFilter, indications }) => {
  const [selectedDiseaseAreas, setSelectedDiseaseAreas] = useState(indications);
  const [selectedDisease, setSelectedDisease] = useState([]);
  const [diseaseFilterOptions, setDiseaseFilterOptions] = useState<string[]>(
    []
  );
  const [selectedColumns, setSelectedColumns] = useState([
    "DiseaseArea",
    "ppm_id", 
    "associated_pgs_id",
    "sampleset_id",
    "performance_source",
    "mapped_trait", 
    "pgs_effect_sizes",
    "classification_metric",
    "other_metrics",
    "covariates",
    "performance_comments"
  ]);
  
  useEffect(() => {
    if (!diseaseAreaFilter) setSelectedDisease(indications);
    else setSelectedDiseaseAreas(indications);
  }, [diseaseAreaFilter, indications]);

  const columnDefs = useMemo(
    () => [
      ...(diseaseAreaFilter
        ? [
            {
              field: "DiseaseArea",
              headerName: "Disease area",
            },
          ]
        : []),
      {
        field: "ppm_id",
        headerName: "PGS Performance Metric ID (PPM)",
      },
      {
        field: "associated_pgs_id",
        headerName: "Evaluated Score",
        cellRenderer: (params: any) => {
          return (
            <a className="underline" target="_blank" href={params.data.pgs_url}>
              {params.data.associated_pgs_id}
            </a>
          );
        },
      },
      {
        field: "sampleset_id",
        headerName: "PGS sample set id (PSS)",

        valueGetter: (params) => `
                <div>
                  <span >${params.data["sampleset_id"]}</span>
                  <p class="text-xs">${params.data["ancestry_broad"]}</p>
                  <div className="flex gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-user-icon lucide-user"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                   <p class="text-xs ">
                   ${params.data["sample_number"]}${" "}individuals </p></div>
                  
                  
                </div>
              `,
        cellRenderer: (params) => parse(params.value),
      },
      {
        field: "performance_source",
        headerName: "Performance Source",

        valueGetter: (params) => `
                <div>
                  <a target="_blank" href=${params.data["performance_source_url"]}>${params.data["performance_source"]}</a>
                  <p class="text-xs">${params.data["first_author"]} et al. ${
          params.data["journal"]
        } (${params.data["date_publication"].split("-")[0]})</p>
                </div>
              `,
        cellRenderer: (params) => parse(params.value),
        minWidth: 300,
      },
      {
        field: "mapped_trait",
        headerName: "Trait",
      },
      {
        field: "pgs_effect_sizes",
        headerName: "PGS effect size (per SD change)",
        valueGetter: (params) =>
          renderPgsEffectSizes(params.data?.pgs_effect_sizes),

        cellRenderer: (params) => parse(params.value),
      },
      {
        headerName: "Classification Metrics",
        field: "classification_metric",
        valueGetter: (params) =>
          renderPgsEffectSizes(params.data?.classification_metrics),

        cellRenderer: (params) => parse(params.value),
      },
      {
        headerName: "Other metrics",
        field: "other_metrics",
        valueGetter: (params) =>
          renderPgsEffectSizes(params.data?.other_metrics),

        cellRenderer: (params) => parse(params.value),
      },
      {
        headerName: "Covariates Included in the Model",
        field: "covariates",
      },
      {
        headerName: "PGS Performance:Other Relevant Information",
        field: "performance_comments",
      },
    ],
    [diseaseAreaFilter]
  );
  
  const dataFilteredByArea = useMemo(() => {
    if (diseaseAreaFilter) {
      return filterByDiseases(
        data,
        selectedDiseaseAreas,
        indications,
        "DiseaseArea"
      );
    }
    return data;
  }, [data, selectedDiseaseAreas, indications, diseaseAreaFilter]);
   useEffect(() => {
   
      const diseases = Array.from(
        new Set(
          dataFilteredByArea.map((item) => capitalizeFirstLetter(item.Disease))
        )
      ).sort() as string[];
      setDiseaseFilterOptions(diseases);
    }, [dataFilteredByArea]);
  const handleColumnChange = (columns) => {
    setSelectedColumns(columns);
  };
  useEffect(() => {
    if (dataFilteredByArea.length > 0) {
      const diseases = [
        ...new Set(
          dataFilteredByArea.flatMap((item) => item.mapped_trait || [])
        ),
      ] as string[];
      if (diseaseAreaFilter) {
        setDiseaseFilterOptions([...diseases.sort()]);
      } else {
        const combinedDiseases = [
          ...new Set([
            ...diseases,
            ...indications.map((indication) => indication.toLowerCase()),
          ]),
        ];
        setDiseaseFilterOptions([...combinedDiseases.sort()]);
      }
    }
  }, [dataFilteredByArea, diseaseAreaFilter, indications]);
  const filteredData = useMemo(() => {
    if (!(selectedDisease.length > 0)) {
      return dataFilteredByArea;
    }
    return dataFilteredByArea.filter(
      (row) =>
        row.mapped_trait &&
        row.mapped_trait.some((d) =>
          selectedDisease.some(
            (selected) => selected.toLowerCase() === d.toLowerCase()
          )
        )
    );
  }, [dataFilteredByArea, selectedDisease]);
  const visibleColumns = useMemo(
    () => columnDefs.filter((col) => selectedColumns.includes(col.field)),
    [columnDefs, selectedColumns]
  );
  return (
    <div className="mt-7" id="PPM">
      <h2 className="text-xl subHeading font-semibold mb-3">
        Performance metrics{" "}
      </h2>
      <p className="my-2 font-medium ">
      The table describes performance matrix of the catalogued evaluations of the associated PGS, displayed as reported by the source studies.
      </p>
      <div className="flex justify-between mb-3">
        <div className="flex gap-4">
          {diseaseAreaFilter && (
            <DiseaseFilter
              allDiseases={indications}
              selectedDiseases={selectedDiseaseAreas}
              onChange={setSelectedDiseaseAreas}
              // disabled={showLoading}
              width={300}
              labelText="Disease Area:"
            />
          )}
          <DiseaseFilter
                allDiseases={diseaseFilterOptions}
                selectedDiseases={selectedDisease}
                onChange={setSelectedDisease}
                // disabled={showLoading}
                width={300}
                labelText="Disease:"
              />
        </div>

        <ColumnSelector
              allColumns={columnDefs}
              defaultSelectedColumns={selectedColumns}
              onChange={handleColumnChange}
            /> 
      </div>

      <Table rowData={filteredData} columnDefs={visibleColumns} />
    </div>
  );
};

export default PPM;
