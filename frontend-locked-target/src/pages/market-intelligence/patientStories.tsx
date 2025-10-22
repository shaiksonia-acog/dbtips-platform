// import {  useEffect  } from "react";
// import { capitalizeFirstLetter } from "../../utils/helper";
import {  Button, Empty } from "antd"; // Import Select from Ant Design
// import { useQuery } from "react-query";
// import { fetchData } from "../../utils/fetchData";
// const { Option } = Select;
// import Table from "../../components/table";
// import LoadingButton from "../../components/loading";
// import ColumnSelector from "../../components/columnFilter";
// import { useChatStore } from "chatbot-component";
import BotIcon from "../../assets/bot.svg?react";
// import { preprocessPatientData } from "../../utils/llmUtils";
// import { convertToArray } from "../../utils/helper";
// import ExportButton from "../../components/testExportButton";
// import ExportButton from "../../components/exportButton";


// const separateByPipeline = ({ value }) => {
//   return capitalizeFirstLetter( value
//     ?.replace(/[\[\]']/g, "")
//     ?.split(", ")
//     ?.join("|"));
// };

const PatientStories = ({ indications }) => {
  // const [selectedDiseases, setSelectedDiseases] = useState(indications);
  // const { register, invoke } = useChatStore();
  // const payload = {
  //   diseases: indications,
  // };
console.log("indications", indications);
  // const {
  //   data,
  //   error,
  //   isLoading: dataLoading,
  // } = useQuery(
  //   ["patientStories", payload],
  //   () => fetchData(payload, "/market-intelligence/patient-stories/"),
  //   {
  //     enabled: !!indications.length ,
  //     refetchOnWindowFocus: false,
  //     staleTime: 5 * 60 * 1000,
  //     refetchOnMount: false,
  //   }
  // );

  // const processedData = useMemo(() => {
  //   if (data) {
  //     return convertToArray(data);
  //   }
  //   return [];
  // }, [data]);
  // const filterData = useMemo(() => {
  //   if (processedData.length > 0) {
  //     // If all diseases are selected (length matches total indications)
  //     return selectedDiseases.length === indications.length
  //       ? processedData
  //       : processedData.filter((row) =>
  //         selectedDiseases.some(
  //           (indication) =>
  //             indication.toLowerCase() === row.Disease.toLowerCase()
  //         )
  //       );
  //   }
  //   return [];
  // }, [processedData, selectedDiseases]);
  // useEffect(() => {
  //   setSelectedDiseases(indications);
  // }, [indications]);
  // const columnDefs = [
  //   {
  //     headerName: "Disease",
  //     field: "Disease",
  //   },

  //   {
  //     headerName: "Title",
  //     field: "title",
  //     cellRenderer: (params) => {
  //       return (
  //         <a href={params.data.url} target="_blank">
  //           {params.value}
  //         </a>
  //       );
  //     },
  //   },
  //   {
  //     headerName: "Published Date",
  //     field: "published_date",
  //     filter: 'agDateColumnFilter',
  //     // This sets the column filter to agDateColumnFilter
  //     filterParams: {
  //       // Customize date filter parameters
  //       comparator: (filterLocalDateAtMidnight, cellValue) => {
  //         // Convert cell value to Date object
  //         const dateParts = cellValue.split(' ')[0].split('-');
  //         const cellDate = new Date(
  //           Number(dateParts[0]),
  //           Number(dateParts[1]) - 1,
  //           Number(dateParts[2])
  //         );

  //         // Compare dates
  //         if (cellDate < filterLocalDateAtMidnight) {
  //           return -1;
  //         } else if (cellDate > filterLocalDateAtMidnight) {
  //           return 1;
  //         }
  //         return 0;
  //       },
  //     },
  //     // Ensure the date column is recognized as a Date type
  //     valueFormatter: (params) => {
  //       const fixedDate = params.value.replace(' ', 'T'); // "2020-10-20T15:22:08"
  //       const date = new Date(fixedDate);

  //       return date.toLocaleDateString('en-GB', {
  //         day: '2-digit',
  //         month: '2-digit',
  //         year: 'numeric',
  //       });
  //     }


  //   },
  //   {
  //     headerName: "Symptoms",
  //     field: "symptoms",
  //     cellRenderer: separateByPipeline,
  //   },
  //   {
  //     headerName: "Challenges Faced During Diagnosis",
  //     field: "challenges_faced_during_diagnosis",
  //     cellRenderer: separateByPipeline,
  //   },
  //   {
  //     headerName: "View Count",
  //     field: "view_count",
  //     valueGetter: (params) => {
  //       return parseInt(params.data.view_count);
  //     },
  //     sort: 'desc',
  //   },
  //   {
  //     headerName: "Channel Name",
  //     field: "channel_name",
  //     cellRenderer: (params) => {
  //       return capitalizeFirstLetter(params.value);
  //     }
  //   },
  //   {
  //     headerName: "Duration (minutes) ",
  //     field: "duration_seconds",
  //     filter: "agNumberColumnFilter",
  //     valueGetter: (params) => {
  //       if (!params.data || params.data.duration_seconds == null) return null;
  //       const totalSeconds = params.data.duration_seconds;
  //       const minutes = Math.floor(totalSeconds / 60);
  //       const seconds = totalSeconds % 60;
  //       return minutes * 60 + seconds;  // Return the raw total seconds (numeric value)
  //     },
  //     cellRenderer: (params) => {
  //       if (params.value == null) return ''; // handle null or empty values
  //       const totalSeconds = params.value;
  //       const minutes = Math.floor(totalSeconds / 60);
  //       const seconds = totalSeconds % 60;
  //       const formattedSeconds = seconds.toString().padStart(2, '0');
  //       return `${minutes}:${formattedSeconds}`; // Display as minutes:seconds
  //     }
  //   },
  //   {
  //     headerName: "Medical History of Patient",
  //     field: "medical_history_of_patient",
  //     cellRenderer: separateByPipeline,
  //   },
  //   {
  //     headerName: "Description",
  //     field: "description",
  //     cellRenderer: (params) => {
  //       return capitalizeFirstLetter(params.value);
  //     },
  //   },

  //   {
  //     headerName: "Patient name",
  //     field: "name",
  //     cellRenderer: (params) => {
  //       return capitalizeFirstLetter(params.value);
  //     },
  //   },
  //   {
  //     headerName: "Current Age",
  //     field: "current_age",
  //   },
  //   {
  //     headerName: "Onset Age",
  //     field: "onset_age",
  //   },
  //   {
  //     field: "sex",
  //     headrName: "Sex",
  //     cellRenderer: (params) => {
  //       return capitalizeFirstLetter(params.value);
  //     }
  //   },
  //   {
  //     headerName: "Location",
  //     field: "location",
  //     cellRenderer: (params) => {
  //       return capitalizeFirstLetter(params.value);
  //     },
  //   },



  //   {
  //     headerName: "Family Medical History",
  //     field: "family_medical_history",
  //     cellRenderer: separateByPipeline,
  //   },


  // ];



  // const [selectedColumns, setSelectedColumns] = useState([
  //   "Disease",
  //   "title",
  //   "published_date",
  //   "symptoms",
  //   "challenges_faced_during_diagnosis",
  //   "view_count",
  //   "channel_name",
  //   "duration_seconds",
  //   "medical_history_of_patient",

  // ]);
  // const visibleColumns = useMemo(() => {
  //   return columnDefs.filter((col) => selectedColumns.includes(col.field));
  // }, [columnDefs, selectedColumns]);
  // const handleColumnChange = (columns: string[]) => {
  //   setSelectedColumns(columns);
  // };


  // const handleDiseaseChange = (value) => {
  //   if (value.includes("All")) {
  //     // If "All" is selected, select all diseases but don't include "All" in display
  //     setSelectedDiseases(indications);
  //   } else if (
  //     selectedDiseases.length === indications.length &&
  //     value.length < indications.length
  //   ) {
  //     // If coming from "all selected" state and deselecting, just use the new selection
  //     setSelectedDiseases(value);
  //   } else {
  //     // Normal selection behavior
  //     setSelectedDiseases(value);
  //   }
  // };
  // const filterData=[]
  // useEffect(() => {
  //   const llmData = preprocessPatientData(filterData);
  //   register("patient_stories", {
  //     disease: ["Friedreich ataxia"],

  //     data: llmData,
  //   });

  //   // return () => {
  //   // 	unregister('pipeline_indications');
  //   // };
  // }, [filterData]);
  // const processedData = []
  // const handleLLMCall = () => {
  //   if (processedData.length === 0) {
  //     message.warning("This feature requires context to be passed to LLM. As there is no data available, this feature cannot be used");
  //     return;
  //   }
  //   invoke("patient_stories", { send: false });
  // };

  return (
    <div className="px-[5vw] py-16 " id="patientStories">
      <div className="flex gap-2">
        <h1 className="text-xl subHeading font-semibold mb-5">
          Patient stories
        </h1>
        <Button
          type="default" // This will give it a simple outline
          // onClick={handleLLMCall}
          className="w-18 h-8 text-blue-800 text-sm flex items-center"
          disabled
        >
          <BotIcon width={16} height={16} fill="#d50f67" />
          <span>Ask LLM</span>
        </Button>
      </div>
      {/* Disease selection dropdown */}

      {/* {dataLoading && <LoadingButton />}
      {error && !dataLoading && (
        <div className="mt-4 h-[50vh]  flex items-center justify-center">
          <Empty description={`${error}`} />
        </div>
      )}
      {filterData && !dataLoading && (
        <div className=" ">
          <div className="my-2 flex justify-between">
            <div>
              <span className="mt-10 mr-1">Disease:</span>
              <Select
                mode="multiple"
                allowClear
                style={{ width: 500 }}
                placeholder="Select Diseases"
                maxTagCount="responsive"
                onChange={handleDiseaseChange}
                value={selectedDiseases} // Set value to selectedDiseases
              >
                <Option value="All">All</Option>
                {indications?.map((disease, index) => (
                  <Option key={index} value={disease}>
                    {disease}
                  </Option>
                ))}
              </Select>
            </div>
            <div className="flex gap-2">
              <div className="flex gap-2 ">
                <ColumnSelector
                  allColumns={columnDefs}
                  defaultSelectedColumns={selectedColumns}
                  onChange={handleColumnChange}
                />
{                   processedData.length>0 &&   <ExportButton fileName="patientStories" endpoint="/market-intelligence/patient-stories/" indications={["Friedreich ataxia"]} />
}
              </div>

           
            </div>
          </div>
          <Table rowData={filterData} columnDefs={visibleColumns} />
        </div>
      )} */}
          <div className="h-[40vh] flex items-center justify-center">
              <Empty description="Available on request" />
            </div>
    </div>
  );
};

export default PatientStories;