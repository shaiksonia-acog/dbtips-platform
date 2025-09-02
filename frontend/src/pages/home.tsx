/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Button,
  Form,
  Select,
  ConfigProvider,
  Tag,
  Popover,
  notification,
  Modal,
} from "antd";
import type { FormProps } from "antd";
import { capitalizeFirstLetter } from "../utils/helper";
import gifImage from "../assets/Merged-dossier (4).png";
import { parseQueryParams } from "../utils/parseUrlParams";
import { fetchData } from "../utils/fetchData";
import { useQuery } from "react-query";
import { Highlight } from "@orama/highlight";
import parse from "html-react-parser";

type FieldType = {
  target?: string;
  indications?: string[];
};

type GeneSuggestion = {
  id: string;
  approvedSymbol: string;
  matched_column: string;
};

type TIndication = {
  id: string;
  name: string;
  matched_column: string;
};

const IndicationsDefaultState: TIndication[] = [];

const highlighter = new Highlight();
const HighlightText = (text: string, searchTerm: string) => {
  return highlighter.highlight(text, searchTerm);
};

const fetchGeneData = async (
  input: string
): Promise<{ data: GeneSuggestion[] }> => {
  const response = await fetch(
    `${import.meta.env.VITE_API_URI}/genes/lexical?query=${input}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  const text = await response.text();
  if (!response.ok) {
    try {
      const json = JSON.parse(text);
      throw new Error(json.message || "An error occurred");
    } catch {
      throw new Error(text);
    }
  }

  return JSON.parse(text);
};

const Home = ({ setAppState }: { setAppState: (prev: any) => any }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const requestIdRef = useRef<number>(0); // To track the latest request
  const [payload, setPayload] = useState(null);
  const [form] = Form.useForm();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalDescription, setModalDescription] = useState<string>("");
  const [targetOptions, setTargetOptions] = useState<GeneSuggestion[]>([]);
  const [confirm, setConfirm] = useState(false);

  const [target, setTarget] = useState<string | undefined>(undefined);
  const [indications, setIndications] = useState<TIndication[]>(
    IndicationsDefaultState
  );
  const [geneLoading, setGeneLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");
  const [geneInput, setGeneInput] = useState("");
  const [selectedIndications, setSelectedIndications] = useState<string[]>([]);

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const { target, indications } = parseQueryParams(queryParams);
  
    const parsedIndications = indications
      ? indications.map((indication: string) =>
          capitalizeFirstLetter(indication)
        )
      : [];
      const uppercaseTarget = target ? target.toUpperCase() : undefined;

    setTarget(uppercaseTarget); // Set to undefined if no target
    setSelectedIndications(parsedIndications);
  
    form.setFieldsValue({
      target: uppercaseTarget, // Set to undefined if no target
      indications: parsedIndications,
    });
  }, [location, form]);

  useEffect(() => {
    const controller = new AbortController();

    if (!input.length) return;
    setLoading(true);
    const HOST = `${import.meta.env.VITE_API_URI}`;

    axios
      .get(`${HOST}/phenotypes/lexical?query=${input}`, {
        signal: controller.signal,
      })
      .then((response) => {
        setIndications(response.data.data ?? []);
      })
      .catch((error) => {
        if (axios.isCancel(error)) {
          console.log("Request canceled:", error.message);
        } else {
          console.error(
            "Error while fetching suggestions/indications: ",
            error.message
          );
        }
      })
      .finally(() => {
        setLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [input]);

  useEffect(() => {
    if (!geneInput.length) {
      setTargetOptions([]);
      return;
    }

    setGeneLoading(true);

    // Generate unique ID for this request
    const requestId = ++requestIdRef.current;

    // Use this specific search term throughout this request lifecycle
    const searchTerm = geneInput;

    fetchGeneData(searchTerm)
      .then((response) => {
        // Only process if this is still the latest request
        if (requestId !== requestIdRef.current) {
          return;
        }

        // Filter and sort results

        setTargetOptions(response.data);
      })
      .catch((error) => {
        if (requestId === requestIdRef.current) {
          // Only handle errors for current request
          console.error(`Error in request #${requestId}:`, error.message);
        }
      })
      .finally(() => {
        if (requestId === requestIdRef.current) {
          // Only update loading state for current request
          setGeneLoading(false);
        }
      });
  }, [geneInput]);

  const handleIndicationSelect = (value: string) => {
    // Capitalize the first letter before adding to state
    const capitalizedValue = capitalizeFirstLetter(value);

    setSelectedIndications((prev) => {
      const isSelected = prev.includes(capitalizedValue);
      const updated = isSelected
        ? prev.filter((item) => item !== capitalizedValue) // Remove if already selected
        : [...prev, capitalizedValue]; // Add if not selected (capitalized)

      form.setFieldsValue({ indications: updated }); // Sync with the Form & session storage
      sessionStorage.setItem("selectedIndications", JSON.stringify(updated));
      setInput(""); // Clear the search input after selection
      return updated;
    });
  };

  const handleTargetSelect = (value: string) => {
    const uppercaseTarget = value?.toUpperCase() ||undefined;

    setTarget(uppercaseTarget); // Set to undefined if empty
    form.setFieldsValue({ target:uppercaseTarget });
  
    // Reset search state cleanly
    requestIdRef.current++; // Invalidate any pending requests
    setGeneInput(""); // Clear input
    setTargetOptions([]); // Clear options
    
    // Force blur the select input to prevent refocus
    setTimeout(() => {
      const selectInput = document.querySelector('.ant-select-selector');
      if (selectInput && selectInput instanceof HTMLElement) {
        selectInput.blur();
      }
      // Alternative: blur any focused element
      if (document.activeElement && document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
      }
    }, 0);
  };

  const {
    data,

    isLoading,
  } = useQuery(
    ["diseaseStatus", payload],
    () => fetchData(payload, "/dossier/dossier-status/"),
    {
      enabled: !!payload,
    }
  );
  const onFinish: FormProps<FieldType>["onFinish"] = (values) => {
    // Use the selectedIndications state (which is already capitalized) instead of form values
    const capitalizedIndications =
      selectedIndications.length > 0
        ? selectedIndications
        : (values.indications || []).map((indication) =>
            capitalizeFirstLetter(indication)
          );

    setPayload({
      target: values.target ? values.target.toUpperCase() : "",
      diseases: capitalizedIndications, // Use capitalized indications
    });
  };

  // Also fix the useEffect that sets appState to ensure consistency
  
  useEffect(() => {
    form.setFieldsValue({
      indications: selectedIndications,
      target: target,
    });
  }, [selectedIndications, target, form]);

  useEffect(() => {
    if (data) {
      const cachedItems = data["cached"] || [];
      const buildingItems = data["building"] || [];
      
      if (cachedItems.length > 0) {
        // Extract cached diseases and target - ensure capitalization
        const cachedDiseases = cachedItems.flatMap(item => 
          (item.diseases || []).map(disease => capitalizeFirstLetter(disease))
        );
        const cachedTarget = cachedItems.find(item => item.target)?.target?.toUpperCase() || null;
        
        // Build navigation parameters
        const params = new URLSearchParams();
        
        if (cachedDiseases.length > 0) {
          const encodedIndications = cachedDiseases
            .map((indication) => `"${indication}"`)
            .join(",");
          params.append('indications', encodedIndications);
        }
        
        if (cachedTarget) {
          params.append('target', cachedTarget);
        }
        
        setAppState((prev) => ({
          ...prev,
          indications: cachedDiseases, // Already capitalized
          target: cachedTarget?.toUpperCase() || "",
        }));
        
        // Check if all requested items are cached
        const totalRequestedDiseases = payload?.diseases?.length || 0;
        const requestedTarget = payload?.target?.toUpperCase();
        const totalCachedDiseases = cachedDiseases.length;
        
        const allDiseasesReady = totalRequestedDiseases === 0 || totalCachedDiseases === totalRequestedDiseases;
        const targetReady = !requestedTarget || cachedTarget?.toUpperCase() == requestedTarget?.toUpperCase();
        
        if (allDiseasesReady && targetReady) {
          // Everything is cached, navigate directly
          console.log("All requested items are cached, navigating to profile page.");
          if (cachedTarget) {
            navigate(`/target-biology?target=${cachedTarget}&indications=${encodeURIComponent(cachedDiseases.map(d => `"${d}"`).join(",") || "")}`);
          } else {
            navigate(`/disease-profile?indications=${encodeURIComponent(cachedDiseases.map(d => `"${d}"`).join(",") || "")}`);
          }
        } else {
          // Some items are still building
          const buildingDiseases = buildingItems.flatMap(item => 
            (item.diseases || []).map(disease => capitalizeFirstLetter(disease))
          );
          const buildingTarget = buildingItems.find(item => item.target)?.target?.toUpperCase() || null;
          
          // Build description for modal
          let description = "";
          const availableItems = [];
          const buildingItemsDesc = [];
          
          if (cachedDiseases.length > 0) {
            availableItems.push(`diseases: ${cachedDiseases.join(", ")}`);
          }
          if (cachedTarget) {
            availableItems.push(`target: ${cachedTarget}`);
          }
          
          if (buildingDiseases.length > 0) {
            buildingItemsDesc.push(`diseases: ${buildingDiseases.join(", ")}`);
          }
          if (buildingTarget) {
            buildingItemsDesc.push(`target: ${buildingTarget}`);
          }
          
          if (availableItems.length > 0) {
            description += `Dossier is available for ${availableItems.join(" and ")}. `;
          }
          if (buildingItemsDesc.length > 0) {
            description += `It will take some time to build the dossier for ${buildingItemsDesc.join(" and ")}. `;
          }
          description += "Do you want to continue?";
          
          setIsModalOpen(true);
          setModalDescription(description);
          
          if (confirm) {
            if (cachedTarget) {
              navigate(`/target-biology?target=${cachedTarget?.toUpperCase()}&indications=${encodeURIComponent(cachedDiseases.map(d => `"${d}"`).join(",") || "")}`);
            } else {
              navigate(`/disease-profile?indications=${encodeURIComponent(cachedDiseases.map(d => `"${d}"`).join(",") || "")}`);
            }
          }
        }
      } else {
        // No cached items available - ensure building items are also capitalized
        const buildingDiseases = buildingItems.flatMap(item => 
          (item.diseases || []).map(disease => capitalizeFirstLetter(disease))
        );
        const buildingTarget = buildingItems.find(item => item.target)?.target || null;
        
        const buildingItemsDesc = [];
        if (buildingDiseases.length > 0) {
          buildingItemsDesc.push(`diseases: ${buildingDiseases.join(", ")}`);
        }
        if (buildingTarget) {
          buildingItemsDesc.push(`target: ${buildingTarget?.toUpperCase()}`);
        }
        
        notification.warning({
          message: "Processing",
          description: `The dossier is being built for ${buildingItemsDesc.join(" and ")}. Please try again later.`,
        });
      }
    }
  }, [data, navigate, payload, confirm, setAppState]);
  const isButtonDisabled = target === "" && selectedIndications.length === 0;

  const dropdownRenderIndications = () => {
    if (loading) return <p className="px-4 py-2">Loading...</p>;
    if (!input.length) {
      return <p className="px-4 py-2">Start typing to search</p>;
    }
    if (!loading && !indications.length) {
      return <p className="px-4 py-2">No data</p>;
    }

    return (
      <ul className="max-h-80 overflow-y-auto text-sm">
        {indications.map((opt) => {
          const capitalizedName = capitalizeFirstLetter(opt.name);
          return (
            <li
              key={opt.id}
              title={capitalizedName}
              onClick={() => handleIndicationSelect(opt.name)} // Pass original name, function will capitalize
              className={`px-4 py-2 rounded ${
                selectedIndications.includes(capitalizedName)
                  ? "bg-[#e6f4ff]"
                  : "hover:bg-gray-100"
              }`}
            >
              <p>{capitalizedName}</p> {/* Display capitalized name */}
              <div className="mt-1">
                <Tag
                  color="green"
                  bordered={false}
                  className="cursor-pointer text-xs"
                >
                  {opt.id}
                </Tag>

                <Popover
                  zIndex={1100}
                  content={
                    <p className="max-w-80 text-sm max-h-52 overflow-y-scroll">
                      {parse(
                        HighlightText(opt.matched_column.split(":")[1], input)
                          .HTML
                      )}
                    </p>
                  }
                  placement="left"
                >
                  <Tag className="cursor-pointer text-xs">
                    {opt.matched_column.split(":")[0]}
                  </Tag>
                </Popover>
              </div>
            </li>
          );
        })}
      </ul>
    );
  };

  const dropdownRenderGene = () => {
    if (geneLoading) return <p className="px-4 py-2">Loading...</p>;
    if (!geneInput.length) {
      return <p className="px-4 py-2">Start typing to search</p>;
    }
    if (!geneLoading && !targetOptions.length) {
      return <p className="px-4 py-2">No data found for '{geneInput}'</p>;
    }

    return (
      <ul className="max-h-80 overflow-y-auto text-sm">
        {targetOptions.map((opt) => (
          <li
            key={opt.id}
            title={opt.approvedSymbol}
            onClick={() => handleTargetSelect(opt.approvedSymbol)}
            className={`px-4 py-2 rounded ${
              target === opt.approvedSymbol
                ? "bg-[#e6f4ff]"
                : "hover:bg-gray-100"
            }`}
          >
            <p>{opt.approvedSymbol}</p>

            <div className="mt-1">
              <Tag
                color="green"
                bordered={false}
                className="cursor-pointer text-xs"
              >
                {opt.id}
              </Tag>

              <Popover
                zIndex={1100}
                content={
                  <p className="max-w-80 text-sm max-h-52 overflow-y-scroll">
                    {parse(
                      HighlightText(opt.matched_column.split(":")[1], geneInput)
                        .HTML
                    )}
                  </p>
                }
                placement="left"
              >
                <Tag className="cursor-pointer text-xs">
                  {opt.matched_column.split(":")[1]}
                </Tag>
              </Popover>
            </div>
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="bg-gradient-to-b h-[86vh] from-indigo-50 to-white hero">
      <div className="max-w-[96rem] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-8">
          <h3 className="text-4xl text-gray-900 font-bold mb-4">
            Disease Biomarker & Target Insights Platform & Services (DBTIPS™)
          </h3>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Your guide to transforming complex data into actionable insights and
            empower target validation, and advancing precision-driven research
            and innovation.
          </p>
        </div>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-12">
          <div>
            <img
              src={gifImage}
              alt="Informative GIF"
              className="w-full h-[60vh] object-contain rounded-lg"
              loading="lazy"
            />
          </div>

          <div className="flex items-center w-full">
            <Form
              form={form}
              layout="vertical"
              labelWrap
              className="max-w-2xl mx-auto mb-16 w-full"
              onFinish={onFinish}
            >
              <ConfigProvider
                theme={{
                  components: {
                    Select: {
                      multipleItemHeightLG: 38,
                    },
                  },
                  token: {
                    controlHeight: 44,
                    paddingSM: 17,
                  },
                }}
              >
                <Form.Item name="target" label="Target:">
                  <Select
                    showSearch={true}
                    searchValue={geneInput}
                    placeholder="Please select a target"
                    allowClear={true}
                    onSearch={(value) => {
                      // Increment request ID to invalidate previous requests
                      requestIdRef.current++;
                      setGeneInput(value);
                    }}
                    value={target ? target.toUpperCase() : undefined} // Fix: only set value if target exists
                    onChange={handleTargetSelect}
                    filterOption={false} // Disable default filtering
                    popupRender={dropdownRenderGene}
                  />
                </Form.Item>
                <Form.Item name="indications" label="Indications:">
                  <Select
                    mode="multiple"
                    showSearch={true}
                    searchValue={input}
                    placeholder="Please select an indication"
                    onSearch={(value) => {
                      setInput(value);
                      if (!value) setIndications(IndicationsDefaultState);
                    }}
                    value={selectedIndications}
                    onChange={(value) => {
                      // Capitalize all values when they come from direct selection
                      const capitalizedValues = value.map((v) =>
                        capitalizeFirstLetter(v)
                      );
                      setSelectedIndications(capitalizedValues);
                      form.setFieldsValue({ indications: capitalizedValues });
                      setInput("");
                    }}
                    popupRender={dropdownRenderIndications}
                  />
                </Form.Item>
              </ConfigProvider>

              <Form.Item>
                <Button
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-6 px-6 rounded-xl font-semibold text-lg transition-all duration-200 flex items-center justify-center gap-2 hover:gap-3"
                  htmlType="submit"
                  disabled={isButtonDisabled}
                  loading={isLoading}
                >
                  Search
                </Button>
              </Form.Item>
            </Form>
          </div>
          <Modal
            centered={true}
            open={isModalOpen}
            onOk={() => {
              setConfirm(true);
              setIsModalOpen(false);
            }}
            onCancel={() => {
              setIsModalOpen(false);
            }}
          >
            <p className="mr-2">{modalDescription}</p>
          </Modal>
        </section>
      </div>
    </div>
  );
};

export default Home;
