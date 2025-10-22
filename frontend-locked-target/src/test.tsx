// "use client"

// import { AgGridReact } from "ag-grid-react"
// import type { ColDef } from "ag-grid-community"
// import { capitalizeFirstLetter } from "./utils/helper"
// import { useMemo, useState } from "react"
// import { Button, Card, Tag, Typography } from "antd"
// import IndicationsSummary from "./pages/market-intelligence/indicationsSummary"

// // const { Title, Paragraph } = Typography
// import originalData from "./primary_progressive_multiple_sclerosis.json"
// // Sample data structure - replace with your actual data array
// // const originalData = [
// //   {
// //     Disease: "primary progressive multiple sclerosis",
// //     OriginalDrugNames:
// //       "alemtuzumab GZ402673, alemtuzumab GZ402673, Methylprednisolone, Acyclovir, Loratadine, Ceterizine, Paracetamol, Dexchlorpheniramine",
// //     NctId: "NCT02583594",
// //     SourceURLs: ["https://clinicaltrials.gov/ct2/show/NCT02583594"],
// //     Status: "COMPLETED",
// //     Phase: "Phase 1",
// //     Sponsor: "Sanofi",
// //     Target: "CD52 | NR3C1 | HUMAN HERPESVIRUS 1 DNA POLYMERASE | HRH1 | PTGS2, FAAH, TRPV1 | HRH1 | ",
// //     Drug: "alemtuzumab | methylprednisolone | acyclovir | loratadine | ceterizine | paracetamol | dexchlorpheniramine",
// //     MechanismOfAction:
// //       "CD52: INHIBITOR | NR3C1: AGONIST | HUMAN HERPESVIRUS 1 DNA POLYMERASE: INHIBITOR | HRH1: AGONIST | PTGS2: INHIBITOR, FAAH: INHIBITOR, TRPV1: OPENER | HRH1: NA | ",
// //     Modality: "Antibody | Small molecule | Small molecule | Small molecule | Small molecule | Small molecule",
// //     ChemblIds: "CHEMBL1201587 | CHEMBL650 | CHEMBL184 | CHEMBL998 | CHEMBL112 | CHEMBL1201353",
// //     ApprovalStatus: " | Not Approved |  |  |  | ",
// //     OfficialTitle:
// //       "A Phase 1, Exploratory, Randomized, Open-label, 2-Arm Study to Characterize the Pharmacodynamics, Pharmacokinetics, Safety, and Tolerability of Alemtuzumab 12mg Administered Subcutaneously or Intravenously in Patients With Progressive Multiple Sclerosis",
// //     PMIDs: [],
// //     OutcomeStatus: "Not Known",
// //     OutcomeReason: "",
// //   },
// //   // Add more objects here as needed
// // ]

// // Function to parse pipe-separated drug data for all trials
// function parseDrugData(dataArray: typeof originalData) {
//   const parsedRows: any[] = []
  
//   dataArray.forEach((data, trialIndex) => {
//     const drugs = data.Drug.split(" | ")
//       .map((d) => d.trim())
//       .filter((d) => d)
//     const targets = data.Target.split(" | ").map((t) => t.trim())
//     const mechanisms = data["Mechanism of Action"].split(" | ").map((m) => m.trim())
//     const chemblIds = data.ChemblIds.split(" | ")
//       .map((c) => c.trim())
//       .filter((c) => c)
//     const modalities = data.Modality.split(" | ")
//       .map((m) => m.trim())
//       .filter((m) => m)
//     const approvalStatuses = data.ApprovalStatus.split(" | ").map((a) => a.trim())
//     const targetTypes = data.TargetType?.split(" | ").map((t) => t.trim()) || []
    
//     const allowedTargetType = ["ORGANISM", "CELL-LINE", "TISSUE", "SUBCELLULAR", "UNKNOWN"];
//     drugs.forEach((drug, drugIndex) => {
//       const targetType = targetTypes[drugIndex] || "";
//       const filterTarget = allowedTargetType.some(type => targetType.includes(type));

//       parsedRows.push({
        
//         ...data,
//         trialIndex: trialIndex + 1,
//         drugIndex: drugIndex + 1,
//         uniqueId: `${trialIndex}-${drugIndex}`, // Unique identifier for each row
//         Drug: capitalizeFirstLetter(drug),
//         Target: filterTarget ? "" : targets[drugIndex] || "",
//         MechanismOfAction: filterTarget ? "" : mechanisms[drugIndex] || "",
//         ChemblIds: chemblIds[drugIndex] || "",
//         Modality: filterTarget ? "" :modalities[drugIndex] || "",
//         ApprovalStatus: approvalStatuses[drugIndex] || "",
//         TargetType: filterTarget ? "" : targetType,
//       })
//     })
//   })
  
//   return parsedRows
// }

// // Custom cell renderer for modality with color coding
// const ModalityCellRenderer = (params: any) => {
//   const modality = params.value
//   const getModalityColor = (mod: string) => {
//     switch (mod.toLowerCase()) {
//       case "antibody":
//         return "blue"
//       case "small molecule":
//         return "green"
//       default:
//         return "default"
//     }
//   }

//   return (
//     <Tag color={getModalityColor(modality)}>
//       {modality}
//     </Tag>
//   )
// }

// // Custom cell renderer for ChEMBL IDs with links
// const ChemblCellRenderer = (params: any) => {
//   const chemblId = params.value
//   if (!chemblId || chemblId.trim() === "") return ""

//   return (
//     <a
//       href={`https://www.ebi.ac.uk/chembl/compound_report_card/${chemblId}/`}
//       target="_blank"
//       rel="noopener noreferrer"
//       className="text-blue-600 hover:text-blue-800 underline font-mono text-sm"
//     >
//       {chemblId}
//     </a>
//   )
// }

// // Custom cell renderer for drug index
// const DrugIndexCellRenderer = (params: any) => {
//   return (
//     <div className="flex items-center justify-center">
//       <Tag color="default">
//         {params.value}
//       </Tag>
//     </div>
//   )
// }

// export default function ClinicalTrialTable() {
//   const [viewMode, setViewMode] = useState<"parsed" | "original">("parsed")

//   const parsedData = useMemo(() => parseDrugData(originalData), [])
//   console.log("Parsed Data:", parsedData)
//   const originalDataArray = useMemo(() => originalData, [])

//   const parsedColumnDefs: ColDef[] = useMemo(
//     () => [
//       // {
//       //   headerName: "Trial #",
//       //   field: "trialIndex",
//       //   width: 80,
//       //   pinned: "left",
//       //   cellRenderer: DrugIndexCellRenderer,
//       // },
//       // {
//       //   headerName: "Drug #",
//       //   field: "drugIndex",
//       //   width: 80,
//       //   pinned: "left",
//       //   cellRenderer: DrugIndexCellRenderer,
//       // },
//       {
//         headerName: "Disease",
//         field: "Disease",
//         width: 200,
//       },
//       {
//         headerName: "Drug Name",
//         field: "Drug",
//         width: 180,
//         pinned: "left",
//         // cellStyle: { fontWeight: "bold", backgroundColor: "#f8f9fa" },
//       },
//       {
//         headerName: "Target",
//         field: "Target",
//         width: 200,
//         cellStyle: { backgroundColor: "#fff3cd" },
//       },
//       {
//         headerName: "Mechanism of Action",
//         field: "MechanismOfAction",
//         width: 250,
//         cellStyle: { backgroundColor: "#d1ecf1" },
//       },
     
//       {
//         headerName: "Modality",
//         field: "Modality",
//         width: 140,
//         cellRenderer: ModalityCellRenderer,
//         cellStyle: { backgroundColor: "#dde0f6" },
//       },
//       {
//         headerName: "Approval Status",
//         field: "ApprovalStatus",
//         width: 130,
//         cellStyle: (params) => {
//           const status = params.value?.toLowerCase();
      
//           if (status === "approved") {
//             return { backgroundColor: "#d4edda", color: "#155724" }; // green background
//           } else if (status === "pending" || status === "in review" || !status) {
//             return { backgroundColor: "#f8f9fa", color: "black" }; // default
//           } else {
//             return { backgroundColor: "#f8d7da", color: "#721c24" }; // red for other statuses
//           }
//         },
//         valueGetter: (params) => {
//           const status = params.data.ApprovalStatus?.toLowerCase();
//           if (status === "approved") {
//             return "Approved";
//           }else {
//             return "Not Approved";
//           }
//         }
//       },
      
//       {
//         headerName: "NCT ID",
//         field: "NctId",
//         width: 120,
//       },
//       {
//         header :"OutcomeStatus",
//         field:"OutcomeStatus"
//       },
     
//       {
//         headerName: "Status",
//         field: "Status",
//         width: 120,
//       },
//       {
//         headerName: "Phase",
//         field: "Phase",
//         width: 100,
//       },
//       {
//         headerName: "Sponsor",
//         field: "Sponsor",
//         width: 120,
//       },
//       {
//         headerName:"Target Type",
//         field:"TargetType",
//         width:150,
//       }
//     ],
//     [],
//   )

//   const originalColumnDefs: ColDef[] = useMemo(
//     () => [
//       {
//         headerName: "NCT ID",
//         field: "NctId",
//         width: 120,
//         pinned: "left",
//         cellStyle: { fontWeight: "bold" },
//       },
//       {
//         headerName: "Disease",
//         field: "Disease",
//         width: 200,
//       },
//       {
//         headerName: "Status",
//         field: "Status",
//         width: 120,
//       },
//       {
//         headerName: "Phase",
//         field: "Phase",
//         width: 100,
//       },
//       {
//         headerName: "Sponsor",
//         field: "Sponsor",
//         width: 120,
//       },
//       {
//         headerName: "Drugs ",
//         field: "Drug",
//         width: 300,
//         tooltipField: "Drug",
//       },
//       {
//         headerName: "Targets",
//         field: "Target",
//         width: 300,
//         tooltipField: "Target",
//       },
//       {
//         headerName: "Mechanisms of Action",
//         field: "Mechanism of Action",
//         width: 300,
//         tooltipField: "MechanismOfAction",
//       },
     
//       {
//         headerName: "Modality",
//         field: "Modality",
//         width: 300,
//         tooltipField: "Modality",
//       },
//     ],
//     [],
//   )

//   const defaultColDef = useMemo(
//     () => ({
//         filter: true,
//         floatingFilter: true,
//         wrapHeaderText: true,
//         // flex: 1,
//         // minWidth: 150,
//         autoHeaderHeight: true,
//         autoHeight: true,
//         sortable: true,
//         wrapText: true,
//         cellStyle: {
//           whiteSpace: "normal",
//           lineHeight: "20px",
//         },
//       tooltipShowDelay: 500,
//     }),
//     [],
//   )

//   return (
//     <div className="w-full h-screen p-4">
//       <div >
//         {/* <Paragraph style={{ marginBottom: 16 }}>
//           {viewMode === "parsed"
//             ? `Showing ${parsedData.length} individual drugs from ${originalData.length} clinical trials. Each row represents one drug with its connected target, mechanism, ChEMBL ID, and modality.`
//             : `Showing ${originalData.length} clinical trials in original format with pipe-separated drug combinations.`}
//         </Paragraph> */}

//         {/* <div className="flex gap-2 mb-4">
//           <Button 
//             type={viewMode === "parsed" ? "primary" : "default"}
//             onClick={() => setViewMode("parsed")}
//           >
//             Individual Drugs View
//           </Button>
//           <Button 
//             type={viewMode === "original" ? "primary" : "default"}
//             onClick={() => setViewMode("original")}
//           >
//             Original Combined View
//           </Button>
//         </div> */}

//         {/* {viewMode === "parsed" && (
//           <Card 
//             title="Drug Relationship Legend" 
//             style={{ marginBottom: 16 }}
//             size="small"
//           >
//             <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
//               <div className="flex items-center gap-2">
//                 <div className="w-4 h-4 bg-gray-100 border"></div>
//                 <span>Drug Name</span>
//               </div>
//               <div className="flex items-center gap-2">
//                 <div className="w-4 h-4 bg-yellow-100 border"></div>
//                 <span>Target</span>
//               </div>
//               <div className="flex items-center gap-2">
//                 <div className="w-4 h-4 bg-blue-100 border"></div>
//                 <span>Mechanism</span>
//               </div>
//               <div className="flex items-center gap-2">
//                 <div className="w-4 h-4 bg-green-100 border"></div>
//                 <span>ChEMBL ID</span>
//               </div>
//               <div className="flex items-center gap-2">
//                 <div className="w-4 h-4 bg-red-100 border"></div>
//                 <span>Modality</span>
//               </div>
//             </div>
//           </Card>
//         )} */}
//       </div>

//       <div className="ag-theme-quartz w-full h-[calc(100vh-200px)] border border-gray-200 rounded-lg shadow-sm">
//         <AgGridReact
//         rowData={viewMode === "parsed" ? parsedData : originalDataArray}
//           columnDefs={viewMode === "parsed" ? parsedColumnDefs : originalColumnDefs}
//           defaultColDef={defaultColDef}
//           enableCellTextSelection={true}
//           ensureDomOrder={true}
//           animateRows={true}
//           rowHeight={50}
//           headerHeight={50}
//           tooltipShowDelay={500}
//           tooltipHideDelay={2000}
//           pagination={true}
//         />
//       </div>
//       <IndicationsSummary indicationData={parsedData as any} />

//       {/* <div className="mt-4 text-sm text-gray-500">
//         {viewMode === "parsed" ? (
//           <>
//             <p>• Each row shows one drug with its connected properties from multiple trials</p>
//             <p>• Trial # indicates which clinical trial the drug comes from</p>
//             <p>• Drug # shows the position of the drug within that trial's pipe-separated list</p>
//             <p>• Color-coded columns show the relationships between drug properties</p>
//             <p>• ChEMBL IDs are clickable links to compound information</p>
//           </>
//         ) : (
//           <>
//             <p>• Original format with pipe-separated values for each trial</p>
//             <p>• Each position in the pipes corresponds to the same drug within that trial</p>
//             <p>• Switch to Individual Drugs View to see parsed relationships across all trials</p>
//           </>
//         )}
//       </div> */}
//     </div>
//   )
// }