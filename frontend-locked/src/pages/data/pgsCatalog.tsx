import { useState, useMemo, useEffect } from "react";
import { useQuery } from "react-query";
import { AgGridReact } from "ag-grid-react";
import { Empty, Select } from "antd";
import { FileText } from "lucide-react";
import parse from "html-react-parser";


// Utils and components
import { fetchData } from "../../utils/fetchData";
import { capitalizeFirstLetter, convertToArray } from "../../utils/helper";
import { filterByDiseases } from "../../utils/filterDisease";
import LoadingButton from "../../components/loading";
import PieChart from "../../components/pieChart";
import ColumnSelector from "../../components/columnFilter";
import DiseaseFilter from "../../components/diseaseFilter";
import CustomHeader from "../../components/customHeader";
import PPM from "./ppm";


// Cell renderers as separate components for clarity
const PieChartRenderer = ({ chartData, symbol, heading }) => (
 <div>
   <PieChart chartData={chartData} symbol={symbol} heading={heading} />
 </div>
);


const GwasRenderer = ({ value }) => (
 <PieChartRenderer
   chartData={value?.gwas}
   symbol="G"
   heading="G- Source of Variant Associations (GWAS)"
 />
);


const DevRenderer = ({ value }) => (
 <PieChartRenderer
   chartData={value?.dev}
   symbol="D"
   heading="D - Score Development/Training"
 />
);


const EvalRenderer = ({ value }) => (
 <PieChartRenderer
   chartData={value?.eval}
   symbol="E"
   heading="E - PGS Evaluation"
 />
);


const PgsCatalog = ({ indications, diseaseAreaFilter }) => {
 const [selectedDisease, setSelectedDisease] = useState([]);
 const [selectedColumns, setSelectedColumns] = useState([
   "DiseaseArea",
   "Disease",
   "mapped_diseases",
   "PGS ID",
   "PGS Publication ID",
   "PGS Reported Trait",
   "PGS Number of Variants",
   "PGS Ancestry Distribution",
   "PGS Scoring File",
   "risk",
   "protective",
   "overall",
 ]);
 const [diseaseFilterOptions, setDiseaseFilterOptions] = useState<string[]>(
   []
 );
 const [selectedDiseaseAreas, setSelectedDiseaseAreas] = useState(indications);


 // API request using react-query
 const {
   data: pgsCatalogData,
   error: pgsCatalogError,
   isLoading,
 } = useQuery(
   ["pgsCatalog", { diseases: indications }],
   () => fetchData({ diseases: indications }, "/genomics/pgscatalog"),
   {
     enabled: !!indications.length,
     refetchOnWindowFocus: false,
     staleTime: 5 * 60 * 1000,
     refetchOnMount: false,
   }
 );


 // Process data only when it changes
 const processedData = useMemo(
   () => (pgsCatalogData ? convertToArray(pgsCatalogData?.pgs_data) : []),
   [pgsCatalogData]
 );
 const processedPPMData = useMemo(
   () => (pgsCatalogData ? convertToArray(pgsCatalogData?.metrics) : []),
   [pgsCatalogData]
 );
 useEffect(() => {
   if (!diseaseAreaFilter) setSelectedDisease(indications);
   else setSelectedDiseaseAreas(indications);
 }, [diseaseAreaFilter, indications]);
 const dataFilteredByArea = useMemo(() => {
   console.log("Filtering data by area...", processedData );
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
 useEffect(() => {
   const diseases = Array.from(
     new Set(
       dataFilteredByArea.map((item) => capitalizeFirstLetter(item.Disease))
     )
   ).sort();
   setDiseaseFilterOptions(diseases);
 }, [dataFilteredByArea]);
 useEffect(() => {
   if (dataFilteredByArea.length > 0) {
     const diseases = [
       ...new Set(
         dataFilteredByArea.flatMap((item) => item.mapped_diseases || [])
       ),
     ];
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


 const [selectedGene, setSelectedGene] = useState<string | null>(null);
 const [geneFilterOptions, setGeneFilterOptions] = useState<string[]>([]);


 useEffect(() => {
   if (processedData.length > 0) {
     const geneSet = new Set<string>();
     processedData.forEach(pgs => {
       if (pgs.targets_score) {
         Object.keys(pgs.targets_score).forEach(gene => geneSet.add(gene.toUpperCase()));
       }
     });
     setGeneFilterOptions(Array.from(geneSet).sort());
     console.log("Gene filter options set:", Array.from(geneSet).sort());
   }
 }, [processedData]);
 // Filter data when processed data or selected diseases change


 const filteredData = useMemo(() => {
   let currentFilteredData = dataFilteredByArea;


   // Apply disease filter
   if (selectedDisease.length > 0) {
     currentFilteredData = currentFilteredData.filter(
       (row) =>
         row.mapped_diseases &&
         row.mapped_diseases.some((d) =>
           selectedDisease.some(
             (selected) => selected.toLowerCase() === d.toLowerCase()
           )
         )
     );
   }


   // Apply gene filter
   if (selectedGene) {
     currentFilteredData = currentFilteredData.filter((pgs) =>
       pgs.targets_score &&
       pgs.targets_score[selectedGene]
     );
   }


   return currentFilteredData;
 }, [dataFilteredByArea, selectedDisease, selectedGene]);


 // Column definitions
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
       field: "mapped_diseases",
       headerName: "Disease",
       cellRenderer: (params) => (
         <div>{params.value ? params.value.join(" | ") : "N/A"}</div>
       ),
     },
     {
       field: "PGS ID",
       headerName: "Polygenic Score ID & Name",


       headerComponent: CustomHeader,
       headerComponentParams: {
         title: "Unique identifier and name of the polygenic score entry",
         displayName: "Polygenic Score ID & Name",
       },
       valueGetter: (params) => `
       <div>
         <a href ="https://www.pgscatalog.org/score/${params.data["PGS ID"]}" target="_blank">${params.data["PGS ID"]}</a>
         <p class="text-xs">(${params.data["PGS Name"]})</p>
       </div>
     `,
       cellRenderer: (params) => parse(params.value),
     },
     {
       field: "PGS Publication ID",
       headerName: "PGS Publication ID (PGP)",
       headerComponent: CustomHeader,
       headerComponentParams: {
         title:
           "Reference to the publication describing how the score was developed and validated.",
         displayName: "PGS Publication ID (PGP)",
       },
       valueGetter: (params) => `
       <div>
         <a href="https://www.pgscatalog.org/publication/${params.data["PGS Publication ID"]}" target="_blank">${params.data["PGS Publication ID"]}</a>
         <p class="text-xs">${params.data["PGS Publication First Author"]} et al. ${params.data["PGS Publication Journal"]} (${params.data["PGS Publication Year"]})</p>
       </div>
     `,
       cellRenderer: (params) => parse(params.value),
       minWidth: 300,
     },
     {
       field: "PGS Reported Trait",
       headerName: "Reported trait",
       headerComponent: CustomHeader,
       headerComponentParams: {
         title: "The trait or phenotype the score predicts.",
         displayName: "Reported trait",
       },
       cellRenderer: (params) => capitalizeFirstLetter(params.value),
     },
     {
       field: "PGS Number of Variants",
       headerName: "Number of Variants",
       headerComponent: CustomHeader,
       headerComponentParams: {
         title:
           "Total number of genetic variants used to calculate the score.",
         displayName: "Number of Variants",
       },
     },
     {
       field: "PGS Ancestry Distribution",
       headerName: "Ancestry distribution",
       headerComponent: CustomHeader,
       headerComponentParams: {
         title:
           "Genetic ancestry composition of populations used for score development (Dev) and evaluation (Eval)",
         displayName: "Ancestry distribution (Dev/Eval)",
       },
       headerClass: "ag-header-cell-center",
       children: [
         {
           headerName: "GWAS",
           field: "PGS Ancestry Distribution",
           cellRenderer: GwasRenderer,
           floatingFilter: false,
           filter: false,
           maxWidth: 70,
           sortable: false,
           headerClass: "ag-header-cell-center",
         },
         {
           headerName: "Dev",
           field: "PGS Ancestry Distribution",
           cellRenderer: DevRenderer,
           floatingFilter: false,
           filter: false,
           maxWidth: 70,
           sortable: false,
           headerClass: "ag-header-cell-center",
         },
         {
           headerName: "Eval",
           field: "PGS Ancestry Distribution",
           cellRenderer: EvalRenderer,
           floatingFilter: false,
           filter: false,
           maxWidth: 70,
           sortable: false,
           headerClass: "ag-header-cell-center",
         },
       ],
     },
   
     ...(selectedGene
       ? [
           {
             field: "risk",
             headerName: `Gene-based Risk Score`,
             headerComponent: CustomHeader,
             headerComponentParams: {
               title: `Percent risk score for gene`,
               displayName: `Gene-based Risk Score (%)`,
             },
                           valueGetter: (params) =>
               params.data?.targets_score?.[selectedGene]?.["Percent risk score for gene"] ?? null,
             cellRenderer: ({ value }) => (value != null ? value.toFixed(2) : "-"),
           },
           {
             headerName: `Gene-based Protection Score `,
             field: "protective",
             headerComponent: CustomHeader,
             headerComponentParams: {
               title: `Percent protective score for gene`,
               displayName: `Gene-based Protective Score (%)`,
             },
             valueGetter: (params) =>
               params.data?.targets_score?.[selectedGene]?.["Percent protective score for gene"] ?? null,
             cellRenderer: ({ value }) => (value != null ? value.toFixed(2) : "-"),
           },
           {
             headerName: `Gene-based Overall Effect`,
             headerComponent: CustomHeader,
             headerComponentParams: {
               title: `Overall effect of gene (in per cent) in disease risk prediction`,
               displayName: `Gene-based Overall Effect (%)`,
             },
             field: "overall",
             valueGetter: (params) =>
               params.data?.targets_score?.[selectedGene]?.[
                 "Overall effect of gene (in per cent) in disease risk prediction"
               ] ?? null,
             cellRenderer: ({ value }) => (value != null ? value.toFixed(2) : "-"),
           },
         ]
       : []),
       {
         field: "PGS Scoring File",
         headerName: "Scoring File (FTP Link)",
         headerComponent: CustomHeader,
         headerComponentParams: {
           title:
             "Downloadable file containing variant weights and scoring details.",
           displayName: "Scoring File (FTP Link)",
         },
         maxWidth: 140,
         floatingFilter: false,
         filter: false,
         cellRenderer: (params) => (
           <a href={params.value} target="_blank" rel="noreferrer">
             <FileText size={35} />
           </a>
         ),
         cellStyle: {
           display: "flex",
           alignItems: "center",
           justifyContent: "center",
         },
       },
   ],
   [diseaseAreaFilter, selectedGene]
 );


 // Filter columns based on user selection
 const visibleColumns = useMemo(
   () => columnDefs.filter((col) => selectedColumns.includes(col.field)),
   [columnDefs, selectedColumns]
 );


 // Event handlers
 const handleColumnChange = (columns) => {
   setSelectedColumns(columns);
 };


 // Default AgGrid props for reuse
 const defaultColDef = {
   sortable: true,
   filter: true,
   resizable: true,
   flex: 1,
   floatingFilter: true,
   cellStyle: {
     whiteSpace: "normal",
     lineHeight: "20px",
   },
   wrapHeaderText: true,
   autoHeight: true,
   wrapText: true,
 };


 return (
   <div id="pgsCatalog" className="mt-7">
     <h2 className="text-xl subHeading font-semibold mb-3">
       Polygenic risk scores
     </h2>


     <p className="my-1">
       Quantifies an individual's genetic susceptibility to{" "}
       {indications.join(", ")} based on multiple risk variants. Select a gene to view gene-based risk scores
     </p>


     {isLoading && <LoadingButton />}


     {pgsCatalogError && (
       <div>
         <Empty description={`${pgsCatalogError}`} />
       </div>
     )}


     {pgsCatalogData && (
       <div>
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
             <div className="flex  gap-2">
             <span className="mt-1 mr-1">Gene: </span>
               <Select
                 allowClear
                 style={{ width: 300 }}
                 placeholder="Select a gene"
                 showSearch
                 value={selectedGene}
                 onChange={setSelectedGene}
                 options={geneFilterOptions.map(gene => ({ label: gene, value: gene }))}
               />
             </div>
           </div>


           <ColumnSelector
             allColumns={columnDefs}
             defaultSelectedColumns={selectedColumns}
             onChange={handleColumnChange}
           />
         </div>


         <div className="ag-theme-quartz h-[70vh]">
           <AgGridReact
             defaultColDef={defaultColDef}
             columnDefs={visibleColumns}
             rowData={filteredData}
             pagination={true}
             paginationPageSize={10}
             enableCellTextSelection={true}
           />
         </div>
         <PPM
           data={processedPPMData}
           diseaseAreaFilter={diseaseAreaFilter}
           indications={indications}
         />
       </div>
     )}
   </div>
 );
};


export default PgsCatalog;



