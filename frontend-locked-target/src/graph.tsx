// import  { useMemo, useState } from "react"
// import { 
//   Building2,
//   CheckCircle,
//   BarChart3,
//   Search,
//   Filter,
//   Table2,
//   TrendingUp,
//   PieChart,
//   Target
// } from "lucide-react"
// import { capitalizeFirstLetter } from "./utils/helper"
// import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart as RechartsPieChart, Cell, ResponsiveContainer, Pie, Label } from "recharts"
// import clinicalTrialsData from "./primary_progressive_multiple_sclerosis.json" // Adjust the import path as necessary
// import Table from "./test"
// import { Select } from "antd"
// const { Option } = Select
// import { ResponsiveSankey } from '@nivo/sankey';


// const colorPalette = [
//   '#8884d8', '#82ca9d', '#ffc658', '#d0ed57', '#a4de6c',
//   '#8dd1e1', '#83a6ed', '#ff7300', '#ff6384', '#36a2eb'
// ];

// const palette = [
//   '#00B3AD',
//   '#FFB74D',
//   '#64B5F6',
//   '#E57373',
//   '#AED581',
//   '#F06292',
// ];

// const StackedTargetChart = ({ trials }) => {
//   const { nodes, links } = useMemo(() => {
//     const targetSet = new Set();
//     const diseaseSet = new Set();
//     const linkMap = new Map();

//     trials.forEach((trial) => {
//       const disease = trial.disease || 'Unknown';
//       const targets = (trial.target ?? '')
//         .split(',')
//         .map((t) => t.trim())
//         .filter(Boolean);

//       diseaseSet.add(disease);

//       targets.forEach((target) => {
//         targetSet.add(target);

//         const key = `${target}→${disease}`;
//         linkMap.set(key, (linkMap.get(key) || 0) + 1);
//       });
//     });

//     const nodes = [
//       ...Array.from(targetSet).map((t) => ({ id: String(t) })),
//       ...Array.from(diseaseSet).map((d) => ({ id: String(d) })),
//     ];

//     const links = Array.from(linkMap.entries()).map(([key, value]) => {
//       const [source, target] = key.split('→');
//       return { source, target, value };
//     });

//     return { nodes, links };
//   }, [trials]);

//   return (
//     <div style={{ height: 600 }}>
//       <ResponsiveSankey
//         data={{ nodes, links }}
//         margin={{ top: 20, right: 100, bottom: 20, left: 100 }}
//         align="justify"
//         colors={{ scheme: 'category10' }}
//         nodeOpacity={1}
//         nodeThickness={15}
//         nodeInnerPadding={4}
//         nodeSpacing={24}
//         linkOpacity={0.5}
//         linkHoverOpacity={0.8}
//         linkBlendMode="multiply"
//         labelPosition="outside"
//         labelOrientation="horizontal"
//         labelPadding={12}
//         animate={true}
//         motionConfig="gentle"
//       />
//     </div>
//   );
// };
// const TargetDiseaseChart = ({ trials }) => {
//   // Preprocess trials to group by target and count diseases
//   const generateChartData = (trials) => {
//     const uniquePairs = new Set();
//     const targetMap = {};
//     const diseaseSet = new Set();

//     trials.forEach(({ target, disease }) => {
//       const targets = target.split(',').map(t => t.trim());

//       targets.forEach(t => {
//         const key = `${t}|||${disease}`; // unique identifier
//         if (!uniquePairs.has(key)) {
//           uniquePairs.add(key);
//           diseaseSet.add(disease);
//           if (!targetMap[t]) targetMap[t] = { target: t };
//           targetMap[t][disease] = (targetMap[t][disease] || 0) + 1;
//         }
//       });
//     });

//     return {
//       data: Object.values(targetMap),
//       diseases: Array.from(diseaseSet),
//     };
//   };

//   const { data, diseases } = generateChartData(trials);

//   const colors = [
//     '#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#a4de6c',
//     '#d0ed57', '#8dd1e1', '#d88884', '#a28ad8', '#d684d8'
//   ];


//   return (
//     <ResponsiveContainer width="100%" height={400}>
//       <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 40 }}>
//         <CartesianGrid strokeDasharray="3 3" />
//         <XAxis dataKey="target" interval={0}
//             angle={-45}
//             textAnchor="end"
//             height={80} />
//         <YAxis allowDecimals={false} />
//         <Tooltip />
//         <Legend />
//         {diseases.map((disease, index) => (
//           <Bar
//             key={String(disease)}
//             dataKey={disease as string}
//             stackId="a"
//             fill={colors[index % colors.length]}
//             name={disease as string}
//           />
//         ))}
//       </BarChart>
//     </ResponsiveContainer>
//   );
// };



// // Parse all drug data from multiple trials
// function parseAllDrugData(trialsData) {
//   return trialsData.flatMap((trial, trialIndex) => {
//     // Add null checks and use the correct property names
//     const drugs = (trial.Drug || "")
//       .split(" | ")
//       .map((d) => d.trim())
//       .filter((d) => d)
//     const targets = (trial.Target || "").split(" | ").map((t) => t.trim())
//     const mechanisms = (trial["Mechanism of Action"] || "").split(" | ").map((m) => m.trim())
//     const chemblIds = (trial.ChemblIds || "")
//       .split(" | ")
//       .map((c) => c.trim())
//       .filter((c) => c)
//     const modalities = (trial.Modality || "")
//       .split(" | ")
//       .map((m) => m.trim())
//       .filter((m) => m)
//     const approvalStatuses = (trial.ApprovalStatus || "").split(" | ").map((a) => a.trim())

//     return drugs.map((drug, drugIndex) => ({
//       id: `${trialIndex}-${drugIndex}`,
//       trialId: trial.NctId,
//       trialIndex,
//       drugIndex: drugIndex + 1,
//       drug:capitalizeFirstLetter(drug),
//       target: targets[drugIndex] || "",
//       mechanism: mechanisms[drugIndex] || "",
//       chemblId: chemblIds[drugIndex] || "",
//       modality: modalities[drugIndex] || "",
//       approvalStatus: approvalStatuses[drugIndex] || "",
//       disease: trial.Disease,
//       phase: trial.Phase,
//       status: trial.Status,
//       sponsor: trial.Sponsor,
//       trialData: trial,
//     }))
//   })
// }

// // Chart colors
// const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d',"#BA68C8"];

// // Recharts Components
// function ModalityChart({ drugs }) {
//   const modalityStats = useMemo(() => {
//     // First, get unique drugs with their modality
//     const uniqueDrugs = drugs.reduce((acc, drug) => {
//       const drugName = drug.drug +"-"+drug.disease
//       const modality = drug.modality || "Unknown"
      
//       if (!acc[drugName]) {
//         acc[drugName] = modality
//       }
//       // If drug appears multiple times with same modality, keep it
//       // If different modalities, keep the first non-"Unknown" one
//       else if (acc[drugName] === "Unknown" && modality !== "Unknown") {
//         acc[drugName] = modality
//       }
//       return acc
//     }, {})
    
//     // Then count occurrences of each modality
//     const stats = Object.values(uniqueDrugs).reduce((acc: Record<string, number>, modality: string) => {
//       acc[modality] = (acc[modality] || 0) + 1
//       return acc
//     }, {} as Record<string, number>)
    
//     return Object.entries(stats).map(([name, value]) => ({ name, value }))
//   }, [drugs])

//   return (
//     <div className="bg-white p-6 rounded-lg shadow-md">
//       <div className="flex items-center gap-2 mb-4">
//         <PieChart className="w-5 h-5" />
//         <h3 className="text-lg font-semibold">Drug Modalities Distribution</h3>
//       </div>
//       <ResponsiveContainer width="100%" height={300}>
//         <RechartsPieChart>
//           <Pie
//             dataKey="value"
//             data={modalityStats}
//             cx="50%"
//             cy="50%"
//             outerRadius={80}
//             fill="#8884d8"
//             label
//           >
//             {modalityStats.map((entry, index) => (
//               <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
//             ))}
//           </Pie>
//           <Tooltip />
//           <Legend />
//         </RechartsPieChart>
//       </ResponsiveContainer>
//     </div>
//   )
// }

// function PhaseChart({ drugs }) {
//   const phaseStats = useMemo(() => {
//     // First, get the maximum phase for each unique drug, but prioritize approved status
//     const drugMaxPhases = drugs.reduce((acc: Record<string, { phase: string; drug: string; disease: string }>, drug: { drug: string; disease: string; phase: string; approvalStatus: string }) => {
//       const drugName = drug.drug + "-" + drug.disease
//       const phase = drug.phase || "Unknown"
//       const approvalStatus = drug.approvalStatus || "Unknown"
      
//       if (!acc[drugName]) {
//         // If drug is approved, mark as "Approved", otherwise use phase
//         acc[drugName] = {
//           phase: approvalStatus === "Approved" ? "Approved" : phase,
//           drug: drug.drug,
//           disease: drug.disease
//         }
//       } else {
//         // If current status is already "Approved", keep it
//         if (acc[drugName].phase === "Approved") {
//           return acc
//         }
        
//         // If new drug is approved, update to "Approved"
//         if (approvalStatus === "Approved") {
//           acc[drugName] = {
//             phase: "Approved",
//             drug: drug.drug,
//             disease: drug.disease
//           }
//           return acc
//         }
        
//         // Otherwise, compare phases and keep the higher one
//         const currentPhase = acc[drugName].phase
//         const newPhase = phase
        
//         // Define phase hierarchy for comparison
//         const phaseHierarchy = {
//           "Early_Phase1": 0,
//           "Phase 1": 1,
//           "Phase1/Phase2": 2,
//           "Phase 2": 3,
//           "Phase2/Phase3": 4,
//           "Phase 3": 5,
//           "Phase 4": 6,
//           "Unknown": -1
//         }
        
//         const currentRank = phaseHierarchy[currentPhase] ?? -1
//         const newRank = phaseHierarchy[newPhase] ?? -1
        
//         if (newRank > currentRank) {
//           acc[drugName] = {
//             phase: newPhase,
//             drug: drug.drug,
//             disease: drug.disease
//           }
//         }
//       }
//       return acc
//     }, {})
    
//     console.log("drugMaxPhases", drugMaxPhases)
    
//     // Group by phase and collect drug-disease pairs
//     const statsByPhase = Object.values(drugMaxPhases).reduce((acc, drugInfo: { phase: string; drug: string; disease: string }) => {
//       const phase = drugInfo.phase
//       if (!acc[phase]) {
//         acc[phase] = {
//           count: 0,
//           drugs: []
//         }
//       }
//       acc[phase].count++
//       acc[phase].drugs.push({
//         drug: drugInfo.drug,
//         disease: (drugInfo as { disease: string }).disease
//       })
//       return acc
//     }, {})
    
//     // Define the order for clinical trial phases and approved status
//     const phaseOrder = {
//       "Early_Phase1": 0,
//       "Phase 1": 1,
//       "Phase1/Phase2": 2,
//       "Phase 2": 3,
//       "Phase2/Phase3": 4,
//       "Phase 3": 5,
//       "Approved": 6,
//       "Phase 4": 7,
//       "Unknown": 8
//     }
    
//     return Object.entries(statsByPhase)
//       .map(([name, data]) => ({ 
//         name, 
//         value: data.count,
//         drugs: data.drugs
//       }))
//       .filter(item => item.name !== "Na")
//       .sort((a, b) => {
//         const orderA = phaseOrder[a.name] ?? 999
//         const orderB = phaseOrder[b.name] ?? 999
//         return orderA - orderB
//       })
//   }, [drugs])
  
//   console.log("phaseStats", phaseStats)
  
//   // Custom tooltip component
//   const CustomTooltip = ({ active, payload, label }) => {
//     if (active && payload && payload.length) {
//       const data = payload[0].payload
//       return (
//         <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
//            <div className="flex items-center justify-between mb-2">
//         <div className="flex items-center space-x-3">
//           <h3 className="text-lg font-bold text-gray-800">{label}</h3>
//         </div>
//         <div className="bg-blue-100 px-3 py-1 rounded-full">
//           <span className="text-blue-700 font-semibold text-sm">
//             {data.value} 
//           </span>
//         </div>
//       </div>
//           {/* <p className="text-blue-600">{`Count: ${data.value}`}</p> */}
//           <div className="mt-2">
//             {/* <p className="font-medium text-sm mb-1">Drugs:</p> */}
//             <div className="max-h-32 overflow-y-auto">
//                 {[...new Set(data.drugs.map((drugInfo) => drugInfo.disease))].map((disease, index) => (
//                 <span key={index}               className="inline-block bg-blue-50 text-blue-700 text-xs font-medium px-3 py-1 rounded-full border border-blue-200 mr-1 mb-1"
// >
//                   {disease as String}
//                 </span>
//                 ))}
             
//             </div>
//           </div>
//         </div>
//       )
//     }
//     return null
//   }
  
//   return (
//     <div className="bg-white p-6 rounded-lg shadow-md">
//       <div className="flex items-center gap-2 mb-4">
//         <BarChart3 className="w-5 h-5" />
//         <h3 className="text-lg font-semibold">Clinical Trial Phases</h3>
//       </div>
//       <ResponsiveContainer width="100%" height={300}>
//         <BarChart data={phaseStats}>
//           <CartesianGrid strokeDasharray="3 3" />
//           <XAxis 
//             dataKey="name" 
//             interval={0}
//             angle={-45}
//             textAnchor="end"
//             height={80}
//           />
//           <YAxis label={{ value: 'Count of Drugs', angle: -90, position: 'insideLeft' }} />
//           <Tooltip content={<CustomTooltip active={undefined} payload={undefined} label={undefined} />} />
//           <Bar dataKey="value" fill="#8884d8" radius={[10, 10, 0, 0]} />
//         </BarChart>
//       </ResponsiveContainer>
//     </div>
//   )
// }
// function ApprovalStatusChart({ drugs }) {
//   const approvalStats = useMemo(() => {
//     // First, get unique drugs with their approval status
//     const uniqueDrugs = drugs.reduce((acc, drug) => {
//       const drugName = drug.drug
//       const status = drug.approvalStatus === "Approved" ? "Approved" : "Not Approved"
      
//       if (!acc[drugName]) {
//         acc[drugName] = status
//       } else {
//         // If drug appears multiple times, prioritize "Approved" status
//         if (status === "Approved") {
//           acc[drugName] = "Approved"
//         }
//       }
//       return acc
//     }, {} as Record<string, string>)
    
//     // Then count occurrences of each approval status
//     const stats = Object.values(uniqueDrugs).reduce((acc: Record<string, number>, status) => {
//       acc[status as string] = (acc[status as string] || 0) + 1
//       return acc
//     }, {} as Record<string, number>)
    
//     return Object.entries(stats).map(([name, value]) => ({ name, value }))
//   }, [drugs])

//   return (
//     <div className="bg-white p-6 rounded-lg shadow-md">
//       <div className="flex items-center gap-2 mb-4">
//         <CheckCircle className="w-5 h-5" />
//         <h3 className="text-lg font-semibold">Approval Status Distribution</h3>
//       </div>
//       <ResponsiveContainer width="100%" height={300}>
//         <BarChart data={approvalStats}>
//           <CartesianGrid strokeDasharray="3 3" />
//           <XAxis dataKey="name" />
//           <YAxis />
//           <Tooltip />
//           <Bar dataKey="value" fill="#82ca9d" />
//         </BarChart>
//       </ResponsiveContainer>
//     </div>
//   )
// }



// const SponsorChart = ({ drugs }) => {
//   const sponsorStats = useMemo(() => {
//     const stats = drugs.reduce((acc, drug) => {
//       const sponsor = drug.sponsor || "Unknown";
//       acc[sponsor] = (acc[sponsor] || 0) + 1;
//       return acc;
//     }, {});
  
//     return Object.entries(stats)
//       .sort(([, a], [, b]) => Number(b) - Number(a))
//       .slice(0, 10)
//       .map(([fullName, value]) => ({
//         name: fullName.length > 20 ? fullName.substring(0, 20) + "..." : fullName,
//         fullName,
//         value,
//       }));
//   }, [drugs]);

//   return (
//     <div style={{ width: '100%', height: 400 }} className="bg-white p-6 rounded-lg shadow-md">
//        <div className="flex items-center gap-2 mb-4">
//         <Building2 className="w-5 h-5" />
//         <h3 className="text-lg font-semibold">Top 10 Sponsors</h3>
//       </div>
//       <ResponsiveContainer width="100%" height="100%">
//         <BarChart
//           data={sponsorStats}
//           layout="vertical"
//           margin={{ top: 20, right: 30, left: 100, bottom: 20 }}
//         >
//           <CartesianGrid strokeDasharray="3 3" />
//           <XAxis type="number" />
//           <YAxis dataKey="name" type="category" />
//           <Tooltip />
//           <Bar dataKey="value" fill="#00b3ad" radius={[0, 10, 10, 0]} name="Number of Drugs" />
//         </BarChart>
//       </ResponsiveContainer>
//     </div>
//   );
// };

// const CustomTooltip = ({ active, payload }) => {
//   if (active && payload && payload.length) {
//     const data = payload[0].payload;
//     return (
//       <div style={{ background: '#fff', border: '1px solid #ccc', padding: 10 }}>
//         <strong>{data.fullName}</strong>
//         <div>Drug Count: {data.value}</div>
//       </div>
//     );
//   }
//   return null;
// };

// const TopTargetsChart = ({ drugs }) => {
//   const topTargets = useMemo(() => {
//     const targetCount = {};

//     drugs.forEach((drug) => {
//       const targets = drug.target?.split(',').map(t => t.trim()).filter(Boolean) || [];
//       targets.forEach(target => {
//         targetCount[target] = (targetCount[target] || 0) + 1;
//       });
//     });

//     return Object.entries(targetCount)
//       .sort(([, a], [, b]) => Number(b) - Number(a))
//       .slice(0, 10)
//       .map(([fullName, value]) => ({
//         name: fullName.length > 20 ? fullName.substring(0, 20) + "..." : fullName,
//         fullName,
//         value,
//       }));
//   }, [drugs]);

//   return (
//     <div style={{ width: '100%', height: 400 }} className="bg-white p-6 rounded-lg shadow-md">
//         <div className="flex items-center gap-2 mb-4">
//         <Target className="w-5 h-5" />
//         <h3 className="text-lg font-semibold">Top 10 targets by drug count</h3>
//       </div>
//       <ResponsiveContainer width="100%" height="100%">
//         <BarChart
//           data={topTargets}
//           layout="vertical"
//           margin={{ top: 20, right: 30, left: 100, bottom: 20 }}
//         >
//           <CartesianGrid strokeDasharray="3 3" />
//           <XAxis type="number" />
//           <YAxis dataKey="name" type="category" />
//           <Tooltip content={<CustomTooltip active={undefined} payload={undefined} />} />
//           <Bar dataKey="value" fill="#64B5F6" radius={[0, 10, 10, 0]} name="Drug Count" />
//         </BarChart>
//       </ResponsiveContainer>
//     </div>
//   );
// };


// // Main Dashboard Component
// export default function ClinicalTrialDashboard() {
//   const [searchTerm, setSearchTerm] = useState("")
//   const [selectedDisease, setSelectedDisease] = useState("all")
//   const [selectedStatus, setSelectedStatus] = useState("all")
//   const [selectedModality, setSelectedModality] = useState("all")
//   const [activeTab, setActiveTab] = useState("charts")

//   const allDrugs = useMemo(() => parseAllDrugData(clinicalTrialsData), [clinicalTrialsData])
//   console.log("all drug",allDrugs)

//   const diseases = useMemo(
//         () => [...new Set(allDrugs.map((drug) => drug.disease).filter((disease): disease is string => typeof disease === "string" && disease.trim() !== ""))] as string[],
//         [allDrugs],
//       )
//   const statuses = useMemo(
//     () => [...new Set(allDrugs.map((drug) => drug.status).filter((status): status is string => typeof status === "string" && status.trim() !== ""))],
//     [allDrugs],
//   )
//   const modalities = useMemo(
//     () => [...new Set(allDrugs.map((drug) => drug.modality).filter((modality) => modality && modality.trim() !== ""))],
//     [allDrugs],
//   )

//   const filteredDrugs = useMemo(() => {
//     return allDrugs.filter((drug) => {
//       const matchesSearch =
//         searchTerm === "" ||
//         drug.drug.toLowerCase().includes(searchTerm.toLowerCase()) ||
//         drug.target.toLowerCase().includes(searchTerm.toLowerCase()) ||
//         drug.disease.toLowerCase().includes(searchTerm.toLowerCase()) ||
//         drug.trialId.toLowerCase().includes(searchTerm.toLowerCase())

//       const matchesDisease = selectedDisease === "all" || drug.disease === selectedDisease
//       const matchesStatus = selectedStatus === "all" || drug.status === selectedStatus
//       const matchesModality = selectedModality === "all" || drug.modality === selectedModality

//       return matchesSearch && matchesDisease && matchesStatus && matchesModality
//     })
//   }, [allDrugs, searchTerm, selectedDisease, selectedStatus, selectedModality])

//   return (
//     <div className="w-full min-h-screen p-6 bg-gray-50">
//       <div className=" px-[5vw]">
//         {/* Header */}
//         <div className="mb-8">
//           <h1 className=" mb-2">Pipeline</h1>
//           {/* <p className="text-gray-600 text-lg">Advanced data visualization with interactive charts</p> */}
//         </div>

//         {/* Search and Filters */}
//         <div className="bg-white p-6 rounded-lg shadow-md mb-6">
//           <div className="flex items-center gap-2 mb-4">
//             <Filter className="w-5 h-5" />
//             <h3 className="text-lg font-semibold">Search & Filters</h3>
//           </div>
          
//           <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
//             <div className="relative">
//               <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
//               <input
//                 type="text"
//                 placeholder="Search drugs, targets, trials..."
//                 value={searchTerm}
//                 onChange={(e) => setSearchTerm(e.target.value)}
//                 className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
//               />
//             </div>
            
//             <Select 
//               value={selectedDisease} 
//               onChange={(value) => setSelectedDisease(value)}
//             //   className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
//             >
//               <Option value="all">All Diseases</Option>
//               {diseases
//                 .filter((disease) => disease && disease.trim() !== "")
//                 .map((disease) => (
//                   <Option key={disease} value={disease}>
//                     {disease.charAt(0).toUpperCase() + disease.slice(1)}
//                   </Option>
//                 ))}
//             </Select>
            
//             {/* <Select 
//               value={selectedStatus} 
//               onChange={(value) => setSelectedStatus(value)}
//             //   className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
//             >
//               <Option value="all">All Statuses</Option>
//               {statuses
//                 .filter((status): status is string => typeof status === "string" && status.trim() !== "")
//                 .map((status) => (
//                   <Option key={status} value={status}>
//                     {String(status)}
//                   </Option>
//                 ))}
//             </Select> */}
            
//             <Select 
//               value={selectedModality} 
//               onChange={(value) => setSelectedModality(value)}
//             //   className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
//             >
//               <Option value="all">All Modalities</Option>
//               {modalities
//                 .filter((modality): modality is string => typeof modality === "string" && modality.trim() !== "")
//                 .map((modality) => (
//                   <Option key={modality as string} value={modality as string}>
//                     {modality as string}
//                   </Option>
//                 ))}
//             </Select>
//           </div>
          
//           <div className="text-sm text-gray-600">
//             Showing {filteredDrugs.length} of {allDrugs.length} drugs
//           </div>
//         </div>

//         {/* Tabs */}
//         <div className="bg-white rounded-lg shadow-md mb-6">
//           <div className="border-b border-gray-200">
//             <nav className="flex space-x-8 px-6">
//               {[
//                   { id: 'cards', label: 'Table', icon: Table2 },
//                 { id: 'charts', label: 'Visualizations', icon: BarChart3 },
//                 { id: 'stats', label: 'Statistics', icon: TrendingUp },
//               ].map(({ id, label, icon: Icon }) => (
//                 <button
//                   key={id}
//                   onClick={() => setActiveTab(id)}
//                   className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm ${
//                     activeTab === id
//                       ? 'border-blue-500 text-blue-600'
//                       : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
//                   }`}
//                 >
//                   <Icon className="w-4 h-4" />
//                   {label}
//                 </button>
//               ))}
//             </nav>
//           </div>

//           <div className="p-6">
//             {activeTab === 'charts' && (
//               <div className="space-y-8">
//                 {/* Charts Grid */}
//                 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
//                   <ModalityChart drugs={filteredDrugs} />
//                   <PhaseChart drugs={filteredDrugs} />
//                 </div>
                
//                 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
//                   {/* <ApprovalStatusChart drugs={filteredDrugs} /> */}
//                   <TopTargetsChart drugs={filteredDrugs} />
//                   {/* <ApprovalStatusChart drugs={filteredDrugs} /> */}
//                   <SponsorChart drugs={filteredDrugs} />
//                 </div>
//              { selectedDisease=="all" &&<div  className="grid grid-cols-1 lg:grid-cols-1 gap-6">
//                   <StackedTargetChart trials={filteredDrugs} />
//                   <TargetDiseaseChart trials={filteredDrugs} />
//                 </div>}


//                 {/* Summary Statistics */}
//                 <div className="bg-white p-6 rounded-lg shadow-md">
//                   <h3 className="text-lg font-semibold mb-4">Key Insights & Statistics</h3>
//                   <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
//                     <div className="bg-gradient-to-r from-blue-50 to-blue-100 p-4 rounded-lg">
//                       <h4 className="font-semibold text-blue-900 mb-2">Total Drugs</h4>
//                       <p className="text-2xl font-bold text-blue-700">{filteredDrugs.length}</p>
//                       <p className="text-sm text-blue-600">Across all trials</p>
//                     </div>
                    
//                     <div className="bg-gradient-to-r from-green-50 to-green-100 p-4 rounded-lg">
//                       <h4 className="font-semibold text-green-900 mb-2">Unique Modalities</h4>
//                       <p className="text-2xl font-bold text-green-700">
//                         {new Set(filteredDrugs.map((d) => d.modality).filter((m) => m)).size}
//                       </p>
//                       <p className="text-sm text-green-600">Different drug types</p>
//                     </div>
                    
//                     <div className="bg-gradient-to-r from-purple-50 to-purple-100 p-4 rounded-lg">
//                       <h4 className="font-semibold text-purple-900 mb-2">Unique Targets</h4>
//                       <p className="text-2xl font-bold text-purple-700">
//                         {new Set(filteredDrugs.map((d) => d.target).filter((t) => t)).size}
//                       </p>
//                       <p className="text-sm text-purple-600">Therapeutic targets</p>
//                     </div>
                    
//                     <div className="bg-gradient-to-r from-orange-50 to-orange-100 p-4 rounded-lg">
//                       <h4 className="font-semibold text-orange-900 mb-2">Approval Rate</h4>
//                       <p className="text-2xl font-bold text-orange-700">
//                         {filteredDrugs.length > 0 ? 
//                           ((filteredDrugs.filter((d) => d.approvalStatus?.includes("Approved")).length / filteredDrugs.length) * 100).toFixed(1) 
//                           : 0}%
//                       </p>
//                       <p className="text-sm text-orange-600">
//                         {filteredDrugs.filter((d) => d.approvalStatus?.includes("Approved")).length} approved
//                       </p>
//                     </div>
//                   </div>
//                 </div>
//               </div>
//             )}

//             {activeTab === 'cards' && (
//             //   <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
//             //     {filteredDrugs.map((drug) => (
//             //       <div key={drug.id} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
//             //         <div className="flex items-center justify-between mb-3">
//             //           <h4 className="font-semibold text-lg text-gray-900">{drug.drug}</h4>
//             //           <span className={`px-2 py-1 text-xs rounded-full ${
//             //             drug.approvalStatus?.includes("Approved") 
//             //               ? 'bg-green-100 text-green-800' 
//             //               : 'bg-gray-100 text-gray-800'
//             //           }`}>
//             //             {drug.approvalStatus?.includes("Approved") ? 'Approved' : 'Not Approved'}
//             //           </span>
//             //         </div>
//             //         <div className="space-y-2 text-sm">
//             //           <p><span className="font-medium">Target:</span> {drug.target}</p>
//             //           <p><span className="font-medium">Modality:</span> {drug.modality}</p>
//             //           <p><span className="font-medium">Phase:</span> {drug.phase}</p>
//             //           <p><span className="font-medium">Status:</span> {drug.status}</p>
//             //           <p><span className="font-medium">Trial ID:</span> {drug.trialId}</p>
//             //         </div>
//             //       </div>
//             //     ))}
//             //   </div>
//             <Table/>
//             )}

//             {activeTab === 'stats' && (
//               <div className="space-y-6">
//                 <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
//                   <div className="bg-white border border-gray-200 rounded-lg p-6">
//                     <h4 className="font-semibold mb-4">Trial Status Breakdown</h4>
//                     {statuses.map((status: string) => {
//                       const count = filteredDrugs.filter(d => d.status === status).length;
//                       const percentage = ((count / filteredDrugs.length) * 100).toFixed(1);
//                       return (
//                         <div key={status} className="flex justify-between py-2">
//                           <span>{status}</span>
//                           <span className="font-medium">{count} ({percentage}%)</span>
//                         </div>
//                       );
//                     })}
//                   </div>
                  
//                   <div className="bg-white border border-gray-200 rounded-lg p-6">
//                     <h4 className="font-semibold mb-4">Modality Distribution</h4>
//                     {modalities.map((modality) => {
//                       const count = filteredDrugs.filter(d => d.modality === modality).length;
//                       const percentage = ((count / filteredDrugs.length) * 100).toFixed(1);
//                       return (
//                         <div key={modality as string} className="flex justify-between py-2">
//                           <span>{modality as string}</span>
//                           <span className="font-medium">{count} ({percentage}%)</span>
//                         </div>
//                       );
//                     })}
//                   </div>
                  
//                   <div className="bg-white border border-gray-200 rounded-lg p-6">
//                     <h4 className="font-semibold mb-4">Disease Areas</h4>
//                     {diseases.map((disease) => {
//                       const count = filteredDrugs.filter(d => d.disease === disease).length;
//                       const percentage = ((count / filteredDrugs.length) * 100).toFixed(1);
//                       return (
//                         <div key={disease} className="flex justify-between py-2">
//                           <span className="truncate">{disease}</span>
//                           <span className="font-medium">{count} ({percentage}%)</span>
//                         </div>
//                       );
//                     })}
//                   </div>
//                 </div>
//               </div>
//             )}

//             {activeTab === 'raw' && (
//               <div className="bg-white border border-gray-200 rounded-lg p-6">
//                 <h4 className="font-semibold mb-4">Raw Trial Data</h4>
//                 <pre className="text-xs bg-gray-50 p-4 rounded-lg overflow-auto max-h-96">
//                   {JSON.stringify(clinicalTrialsData, null, 2)}
//                 </pre>
//               </div>
//             )}
//           </div>
//         </div>
//       </div>
//     </div>
//   )
// }