import { useState, useRef, useEffect } from "react";
import { Card, Button, Descriptions, Badge } from "antd";
import { AgGridReact } from "ag-grid-react";
import { capitalizeFirstLetter } from "../../utils/helper";

const DataCard = ({ diseaseData }) => {
  const {
    GseID,
    Title,
    Organism,
    Platform,
    Design,
    PubMedIDs,
    Disease,
    Samples,
    StudyType,
  } = diseaseData;
  const [isExpanded, setIsExpanded] = useState(false);
  const toggleExpand = () => setIsExpanded(!isExpanded);
  const [isOverflown, setIsOverflown] = useState(false);
  const paragraphRef = useRef(null);

  useEffect(() => {
    if (paragraphRef.current) {
      const { scrollHeight, clientHeight } = paragraphRef.current;
      setIsOverflown(scrollHeight - 20 > clientHeight);
    }
  }, [Design[0]]);

  const items = [
    {
      key: "1",
      label: "Title",
      children: Title ? Title[0] : "",
      span: 2,
    },
    {
      key: "6",
      label: "Disease",
      children: Disease ? capitalizeFirstLetter(Disease) : "",
    },

    {
      key: "3",
      label: "Platform",
      children: Platform
        ? Object.entries(Platform)
            .map(([key, value]) => `${key}: ${value}`)
            .join(", ")
        : "",
      span: 2,
    },
    {
      key: "5",
      label: "Organism",
      children: Organism ? Organism.join(",  ") : "",
    },

    {
      key: "4",
      label: "Design",
      children: Design ? (
        <div>
          <p
            ref={paragraphRef}
            className={`transition-all duration-300 ease-in-out ${
              isExpanded ? "overflow-visible" : "overflow-hidden"
            }`}
            style={{
              WebkitBoxOrient: "vertical",
              display: "-webkit-box",
              maxHeight: isExpanded ? "none" : "4.5rem",
            }}
          >
            {Design[0]}
          </p>
          {isOverflown && (
            <button
              onClick={toggleExpand}
              className={`text-blue-500 ${isExpanded ? "mt-5" : "mt-2"}`}
            >
              {isExpanded ? "Show less" : "Show more"}
            </button>
          )}
        </div>
      ) : (
        ""
      ),
      span: 2,
    },
    {
      key: "2",
      label: "Publication",
      children:
        PubMedIDs && PubMedIDs.length > 0
          ? PubMedIDs.map((id, index) => (
              <span key={id}>
                <a
                  href={`https://pubmed.ncbi.nlm.nih.gov/${id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {id}
                </a>
                {index < PubMedIDs.length - 1 && ", "}
              </span>
            ))
          : "",
    },
    { key: "6", label: "", children: "", span: 2 },

    { key: "7", label: "Study type", children: StudyType ? StudyType : "" },
  ];

  const [showTable, setShowTable] = useState(false);

  const handleMoreClick = () => {
    setShowTable(!showTable);
  };

  const columnDefs = [
    { headerName: "Sample id", field: "SampleID", flex: 1 },
    { headerName: "Tissue type", field: "TissueType", flex: 1 },
    {
      headerName: "Characteristics",
      field: "Characteristics",
      flex: 5,
      cellRenderer: ({ value }) => (
        <div>
          {value.map((item, index) => {
            const [label, ...rest] = item.split(":");
            const valueText = rest.join(":").trim();
            return (
              <span key={index}>
                <strong>{label.trim()}:</strong> {valueText}{" "}
              </span>
            );
          })}
        </div>
      ),
    },
  ];

  return (
    <Card
      title={<span className="custom-card-title">GEO accession: {GseID}</span>}
      bordered={true}
      className="mt-3"
      size="small"
      style={{ backgroundColor: "rgba(255, 255, 255, 0.0)", color: "white" }}
      extra={
        <>
          <Badge
            count={Samples.length}
            style={{ backgroundColor: "#5294da" }}
            overflowCount={1000}
          >
            <Button type="primary" onClick={handleMoreClick}>
              {showTable ? "Hide samples" : "Show samples"}
            </Button>
          </Badge>
        </>
      }
    >
      <Descriptions items={items} />
      {showTable && (
        <div
          className="ag-theme-quartz mt-5"
          style={{ height: 400, width: "100%" }}
        >
          <AgGridReact
            defaultColDef={{
              filter: true,
              floatingFilter: true,
              autoHeight: true,
              wrapText: true,
              cellStyle: { whiteSpace: "normal", lineHeight: "20px" },
            }}
            columnDefs={columnDefs}
            rowData={Samples}
            pagination={true}
            paginationPageSize={20}
          />
        </div>
      )}
    </Card>
  );
};

export default DataCard;
