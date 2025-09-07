/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { Empty, Select, message, Tooltip, Button,Tag,Modal } from "antd";
import LoadingButton from "../../components/loading";
import parse from "html-react-parser";
import { fetchData } from "../../utils/fetchData";
import { useQuery } from "react-query";
import { capitalizeFirstLetter } from "../../utils/helper";
import { useChatStore } from "chatbot-component";
import BotIcon from "../../assets/bot.svg?react";
import Exportbutton from "../../components/exportButton";
import { preprocessLiteratureData } from "../../utils/llmUtils";
const { Option } = Select;

function convertToArray(data) {
  const result = [];
  Object.keys(data).forEach((disease) => {
    data[disease]["literature"].forEach((record) => {
      result.push({
        ...record,
        Disease: capitalizeFirstLetter(disease), // Add the disease key
      });
    });
  });
  return result;
}

const Evidence = ({target,indications}) => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [modalContent, setModalContent] = useState("");
  const [modalTitle, setModalTitle] = useState("");

  const showModal = (content,title) => {
    setModalContent(content);
    setModalTitle(title);
    setIsModalVisible(true);
  };



  const handleCancel = () => {
    setIsModalVisible(false);
  };

  
  const [selectedIndication, setSelectedIndication] = useState(indications);
  const [selectedLiterature, setSelectedLiterature] = useState([]);
  const { register, invoke } = useChatStore();

  const payload = {
    diseases: indications,
    target: target,
  };

  const {
    data: evidenceLiteratureData,
    error: evidenceLiteratureError,
    isLoading: evidenceLiteratureLoading,
    isFetching: evidenceLiteratureFetching,
  } = useQuery(
    ["evidenceLiterature", payload],
    () => fetchData(payload, "/evidence/target-literature/"),
    {
      enabled: !!target,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );
  useEffect(() => {
    setSelectedIndication(indications);
  }, [indications]);
  const processedData = useMemo(() => {
    if (evidenceLiteratureData) {
      return convertToArray(evidenceLiteratureData);
    }
    return [];
  }, [evidenceLiteratureData]);


  const rowData = useMemo(() => {
    if (processedData.length > 0) {
      return selectedIndication.length === indications.length
        ? processedData
        : processedData.filter((row) =>
            selectedIndication.some(
              (indication) =>
                indication.toLowerCase() === row.Disease.toLowerCase()
            )
          );
    }
    return [];
  }, [processedData, selectedIndication]);

  const handleSelect = (value: string[]) => {
    if (value.includes("All")) {
      // If "All" is selected, select all diseases but don't include "All" in display
      setSelectedIndication(indications);
    } else if (
      selectedIndication.length === indications.length &&
      value.length < indications.length
    ) {
      // If coming from "all selected" state and deselecting, just use the new selection
      setSelectedIndication(value);
    } else {
      // Normal selection behavior
      setSelectedIndication(value);
    }
  };

  const onSelectionChanged = (event: any) => {
    const selectedNodes = event.api.getSelectedNodes();
    const selectedCount = selectedNodes.length;

    if (selectedCount > 10) {
      // Deselect the latest selection
      const lastSelectedNode = selectedNodes[selectedNodes.length - 1];
      lastSelectedNode.setSelected(false);
      message.warning("You can select a maximum of 10 rows.");
    } else {
      const selectedData = selectedNodes.map((node: any) => node.data);
      setSelectedLiterature(selectedData);
    }
  };
  const showLoading = evidenceLiteratureLoading || evidenceLiteratureFetching;

  useEffect(() => {
    if (selectedLiterature?.length > 0) {
      const llmData = preprocessLiteratureData(selectedLiterature);
      const urls = selectedLiterature.map((data: any) => data.PubMedLink);
      const diseases = [
        ...new Set(selectedLiterature.map((data: any) => data.Disease)),
      ];
      // console.log(llmData);
      register("target_literature", {
        urls: urls,
        target: target,
        diseases: diseases,
        data: llmData,
      });
    }

    // return () => {
    // 	unregister('pipeline_indications');
    // };
  }, [selectedLiterature]);

  const handleLLMCall = () => {
    if(processedData.length===0){
      message.warning("This feature requires context to be passed to LLM. As there is no data available, this feature cannot be used");
      return;
    }
    invoke("target_literature", { send: false });
  };

  return (
    <div className=" mt-8  ">
      <section id="literature-evidence " className="px-[5vw]">
        <div className="flex space-x-5 items-center">
          <h1 className="text-3xl font-semibold">Literature repository</h1>
          <Tooltip title="Please select articles to ask LLM">
            <Button
              type="default" // This will give it a simple outline
              onClick={handleLLMCall}
              className="w-18 h-8 text-blue-800 text-sm flex items-center"
            >
              <BotIcon width={16} height={16} fill="#d50f67" />
              <span>Ask LLM</span>
            </Button>
          </Tooltip>
        </div>
       { indications.length>0 ?<p className="my-2  font-medium ">
          This section offers a curated collection of recent research articles
          highlighting role of {target} in {indications.join(", ")}.
        </p> : 
        <p className="my-2  font-medium ">
          This section offers a curated collection of recent research articles
          highlighting role of {target} in various diseases.
        </p>
       }
        

        {showLoading && <LoadingButton />}

        {evidenceLiteratureError &&
          !evidenceLiteratureLoading &&
          !evidenceLiteratureData && (
            <div className="h-[40vh] flex items-center justify-center">
              <Empty description={String(evidenceLiteratureError)} />
            </div>
          )}
        {!showLoading && !evidenceLiteratureError && evidenceLiteratureData &&(
          <div className="flex justify-between mb-3">
          {  indications.length>0 ?  <div>
              <span className="mt-10 mr-1">Disease: </span>
              <span>
                <Select
                  style={{ width: 300 }}
                  onChange={handleSelect}
                  showSearch={false}
                  value={selectedIndication}
                  mode="multiple"
                  maxTagCount="responsive"
                  disabled={evidenceLiteratureLoading}
                >
                  <Option value="All">All</Option>
                  {indications.map((indication) => (
                    <Option key={indication} value={indication}>
                      {indication}
                    </Option>
                  ))}
                </Select>
              </span>
             
            </div>:<div></div>}
            <Exportbutton
            endpoint="/evidence/target-literature/"
            fileName="literature_reviews"
            indications={indications}
            target={target}
          />
          </div>
        )}

        {!showLoading && !evidenceLiteratureError && rowData.length > 0 && (
          <>
            <div className="ag-theme-quartz h-[80vh] ">
              <AgGridReact
                defaultColDef={{
                  flex: 1,
                  filter: true,
                  sortable: true,
                  floatingFilter: true,
                  headerClass: "font-semibold",
                  autoHeight: true,
                  wrapText: true,
                  cellStyle: { whiteSpace: "normal", lineHeight: "20px" },
                }}
                columnDefs={[
                  {
                    headerName: '',
                    field:"checkbox",
                    checkboxSelection: true,
                    filter: false,
                    flex: 0.5,
                  },
                  ...(indications.length > 0
                    ? [
                        {
                          field: "Disease",
                          headerName: "Disease",
                          flex: 3,
                        },
                      ]
                    : []),
                  { field: 'Year' },
                  {
                    field: 'Qualifers',
                    headerName: 'Category',
                    flex: 1,
                    valueFormatter: (params) => {
                      if (params.value) {
                        return params.value.join(', ');
                      }
                      return '';
                    },
                  },
                  {
                    field: 'Title',
                    headerName: 'Title',
                    flex: 6,
                    cellRenderer: (params) => {
                      return (
                        <a href={params.data.PubMedLink} target='_blank'>
                          {parse(params.value)}
                        </a>
                      );
                    },
                  },
                  {
                    headerName: 'Authors',
                    field:"authors",
                    cellRenderer: (params) => {
                      const authors = params.value;
                      
                      if (!authors || authors.length === 0) {
                        return "";
                      }
                      
                      // Show all authors if there are 4 or fewer
                      if (authors.length <= 4) {
                        return (
                        <div>
                           {authors.join(', ')}
                        </div>
                        );
                      }
                      
                      // For more than 4 authors, show first 3 and last one with tooltip
                      const displayText = ` ${authors.slice(0, 3).join(', ')}, .... , ${authors[authors.length - 1]}`;
                      const allAuthors = ` ${authors.join(', ')}`;
                      
                      return (
                        <Tooltip title={allAuthors} placement="topLeft">
                        <div className="truncated-authors">
                          {displayText}
                        </div>
                        </Tooltip>
                      );
                      },
                    flex:2
                  },
                  {
                    field:"citedby",
                    headerName:"Cited by",
                    flex:1
                  },
                  {
                    field:"tables_analysis",
                    headerName:"Tables Analysis",
                    flex:2,
                    
                    cellRenderer: (params) => {
                      const content = params.value;
                      if (!content || content.length === 0) {
                        return "";
                      }
                      return (
                        <Tag color="geekblue" className="cursor-pointer mt-2" onClick={() => showModal(content,"Tables Analysis")}>
                          View Analysis
                        </Tag>
                      );
                    }
                  },
                  {field:"supplementary_analysis",headerName:"Supplementary File ",flex:2, cellRenderer: (params) => {
                    const content = params.value;
                    if (!content) {
                      return "";
                    }
                    return (
                      <Tag color="geekblue" className="cursor-pointer mt-2" onClick={() => showModal(content, "Supplementary Analysis")}>
                        View Analysis
                      </Tag>
                    );
                  }},
                ]}
                rowData={rowData}
                rowSelection="multiple"
                pagination={true}
                rowMultiSelectWithClick={true}
                onSelectionChanged={onSelectionChanged}
				    enableCellTextSelection={true}

              />
            </div>
          </>
        )}

        {!evidenceLiteratureLoading &&
          !evidenceLiteratureError &&
          evidenceLiteratureData &&
          rowData.length === 0 && (
            <div className="h-[40vh] flex items-center justify-center">
              <Empty description="No  data available" />
            </div>
          )}

        {/* <AskLLM target={target} indications={indications} /> */}
      </section>
      <Modal title={modalTitle} open={isModalVisible}  onCancel={handleCancel} footer={false} width={800} >
        {typeof modalContent === 'string' ? (
          <p>{modalContent}</p>
        ) :(
          Array.isArray(modalContent) && (modalContent as string[]).map((item, index) => {
            const [desc, inference] = item.replace("Description:", "").split("| Inference:");
        
            // detect "Table X"
            const tableMatch = desc.match(/^(Table\s*\d+)/i);
            const restDesc = tableMatch ? desc.replace(tableMatch[0], "").replace("|", "").trim() : desc.trim();
        
            return (
              <div
                className={`mb-2 pb-2 ${index !== (modalContent as string[]).length - 1 ? 'border-b-2' : ''}`}
                key={index}
              >
                {/* Table label */}
                {tableMatch && (
                  <p><strong>{tableMatch[0]}:</strong></p>
                )}
        
                {/* Description */}
                <p>
                  <strong>Description:</strong> {restDesc}
                </p>
        
                {/* Inference */}
                {inference && (
                  <p>
                    <strong>Inference:</strong> {inference.trim()}
                  </p>
                )}
              </div>
            );
          })
        )
        
        }
      </Modal>
    </div>
  );
};

export default Evidence;