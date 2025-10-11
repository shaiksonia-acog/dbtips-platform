import { AgGridReact } from "ag-grid-react";
import { fetchData } from "../../utils/fetchData";
import { useQuery } from "react-query";
import { Empty, Tooltip } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";

import LoadingButton from "../../components/loading";

declare global {
  namespace JSX {
    interface IntrinsicElements {
      "wc-go-ribbon": any;
    }
  }
}
interface CustomHeaderProps {
  displayName?: string;
}
const CustomHeader: React.FC<CustomHeaderProps> = (props) => {
  return (
    <div className="flex items-center">
      <span className="mr-1">{props.displayName}</span>
      <Tooltip
        title={
          <div>
            <span>Source:</span>{" "}
            <a
              href="https://geneontology.org/docs/guide-go-evidence-codes/"
              target="_blank"
              className="underline"
            >
              {" "}
              Guide to GO evidence codes
            </a>
          </div>
        }
      >
        <InfoCircleOutlined className="mr-2" />
      </Tooltip>
    </div>
  );
};
const fetchOntologyRibbon = async (hgncId: string) => {
  const response = await fetch(
    `https://api.geneontology.org/api/ontology/ribbon/?subset=goslim_agr&subject=${hgncId}`
  );

  if (!response.ok) {
    // Try to extract detailed error information from the response body
    const errorDetails = await response.json().catch(() => null);
    const errorMessage =
      errorDetails?.message || `HTTP Error: ${response.status}`;
    throw new Error(errorMessage);
  }

  return response.json();
};
const Ontology = ({ hgnc_id, target }) => {
  const payload = {
    target: target,
  };

  const {
    data: targetOntologyData,
    error: targetOntologyError,
    isLoading: targetOntologyLoading,
  } = useQuery(
    ["targetOntology", payload],
    () => fetchData(payload, "/target-profile/ontology/"),
    {
      enabled: !!target,
    }
  );
  const { data, error, isLoading } = useQuery(
    ["ontologyRibbon", hgnc_id], // Use HGNC ID in the query key
    () => fetchOntologyRibbon(hgnc_id), // Pass HGNC ID to fetch function
    {
      enabled: !!hgnc_id, // Only fetch if hgncId is provided
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );
  console.log(data);
  console.log("error", error);
  return (
    <section id="ontology" className="mt-12 px-[5vw]">
      <h1 className="text-3xl font-semibold">Ontology</h1>
      <p className="mt-2 font-medium">
        This section categorizes the target protein's role in cellular and
        biological systems into three aspects:
      </p>
      <ul className="list-disc pl-6  space-y-2">
        <li>
          <span className="font-semibold">Cellular component:</span> Where the
          gene product is active (e.g., nucleus, cytoplasm).
        </li>
        <li>
          <span className="font-semibold">Molecular function: </span> Specific
          biochemical activities (e.g., kinase activity, DNA binding).
        </li>
        <li>
          <span className="font-semibold">Biological process: </span>Broader
          pathways or objectives the gene product supports (e.g., immune
          response, cell cycle regulation).
        </li>
      </ul>

      {targetOntologyLoading ? (
        <LoadingButton />
      ) : targetOntologyError ? (
        <div className="ag-theme-quartz h-[80vh] max-h-[480px] mt-4 flex items-center justify-center">
          <Empty description="Error" />
        </div>
      ) : !targetOntologyData &&
        !targetOntologyError &&
        !targetOntologyLoading ? (
        <div className="h-[40vh] justify-center items-center flex">
          <Empty description="No data available" />
        </div>
      ) : (
        <div>
          <div className="ag-theme-quartz h-[80vh] max-h-[480px] mt-4">
            <AgGridReact
              defaultColDef={{
                headerClass: "font-semibold",
                flex: 1,
                sortable: true,
                filter: true,
                floatingFilter: true,
                autoHeight: true,
                wrapText: true,
                cellStyle: { whiteSpace: "normal", lineHeight: "20px" },
              }}
              columnDefs={[
                { field: "GO ID" },
                {
                  field: "Name",
                  flex: 2,
                  headerName: "Term",
                },
                { field: "Aspect", headerName: "GO category" },
                {
                  field: "Evidence",
                  headerComponentParams: {
                    displayName: "Evidence code",
                  },
                  headerComponent: CustomHeader,
                },

                { field: "Gene Product", headerName: "Gene product" },
                {
                  field: "Source",
                  cellRenderer: (params) => (
                    <a target="_blank" href={params.data.Link}>
                      {params.value}
                    </a>
                  ),
                  headerName: "Evidence",
                },
              ]}
              rowData={targetOntologyData?.ontology}
              pagination={true}
			  enableRangeSelection={true}
			  enableCellTextSelection={true}
            />
          </div>
          {}
          <div className="mt-8 overflow-x-scroll">
            {/*  @ts-ignore */}
            {isLoading && <LoadingButton />}
            {!error && !isLoading && (
              <div>
                <wc-go-ribbon subjects={hgnc_id}></wc-go-ribbon>
                <p slot="description" className=" text-[#7b7b7b] italic">
                  dark blue for higher volume and light blue for lower volume.
                </p>
              </div>
            )}
            {error && (
              <div>
                <p>
                  No Uniprot KB IDs found for {hgnc_id},Gene Ribbon cannot
                  render GO annotations for {hgnc_id}.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
};

export default Ontology;
