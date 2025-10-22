import React, { useState, useEffect } from "react";
import { Collapse, theme } from "antd";
import { CaretRightOutlined } from "@ant-design/icons";
import { fetchData } from "../../utils/fetchData";
import OntologySubgraph from "./ontology-subgraph";
import LoadingButton from "../../components/loading";
// Types
interface ApiResponse {
  data: any;
}

interface OntologyProps {
  indications: string[];
}

interface LoadingState {
  [key: string]: boolean;
}

interface DataState {
  [key: string]: ApiResponse["data"] | null;
}

const Ontology: React.FC<OntologyProps> = ({ indications }) => {
  const [loading, setLoading] = useState<LoadingState>({});
  const [data, setData] = useState<DataState>({});
  const [activeKeys, setActiveKeys] = useState<string[]>(["1"]); // Track active keys
  const { token } = theme.useToken();

  const panelStyle: React.CSSProperties = {
    marginBottom: 5,
    background: "rgb(235 235 235)",
    borderRadius: token.borderRadiusLG,
    border: "none",
    fontFamily: "Poppins",
    padding: "0.3rem 0",
  };

  // Fetch data for panel
  const fetchPanelData = async (label: string) => {
    if (data[label] || loading[label]) return;

    setLoading((prev) => ({ ...prev, [label]: true }));

    try {
      const payload = { disease: label };

      const response = await fetchData(payload, "/disease-profile/ontology/");

      setData((prev) => ({
        ...prev,
        [label]: response.data,
      }));
    } catch (error) {
      setData((prev) => ({
        ...prev,
        [label]: null,
      }));
    } finally {
      setLoading((prev) => ({ ...prev, [label]: false }));
    }
  };

  // Handle panel change
  const handleCollapseChange = (keys: string | string[]) => {
    const panelKeys = Array.isArray(keys) ? keys : [keys];
    setActiveKeys(panelKeys);

    panelKeys.forEach((key) => {
      const label = indications[parseInt(key, 10) - 1];
      if (label) {
        fetchPanelData(label);
      }
    });
  };

  // Fetch initial data
  useEffect(() => {
    if (indications.length > 0) {
      const firstLabel = indications[0];
      setLoading((prev) => ({ ...prev, [firstLabel]: true }));
      fetchPanelData(firstLabel);
    }
  }, [indications]); // Depend on indications array

  // Generate items for Collapse component
  const items = indications.map((label, index) => ({
    key: String(index + 1),
    label: label,
    style: panelStyle,
    children: (
      <div>
        {loading[label] ? (
          <LoadingButton />
        ) : data[label] ? (
          <OntologySubgraph name={label} dagData={data[label]} />
        ) : (
          <LoadingButton /> // Show loading while initial data is being fetched
        )}
      </div>
    ),
  }));

  return (
    <article id="disease-ontology" className="mt-12 bg-gray-50 py-20 px-[5vw]">
      <h1 className="text-3xl font-semibold mb-3">Ontology</h1>
      <p className="my-3  font-medium">
        This section presents the disease hierarchy as an ontology, enabling
        users to visualize disease origins, branch nodes, and shared connections
        between diseases.
      </p>
      <Collapse
        items={items}
        bordered={false}
        activeKey={activeKeys}
        defaultActiveKey={["1"]}
        onChange={handleCollapseChange}
        expandIcon={({ isActive }) => (
          <CaretRightOutlined rotate={isActive ? 90 : 0} />
        )}
      />
    </article>
  );
};

export default Ontology;
