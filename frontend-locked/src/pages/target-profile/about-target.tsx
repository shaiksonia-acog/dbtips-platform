import { AgGridReact } from "ag-grid-react";
import { Tooltip, Empty } from "antd";
import { convertObjectToArray } from "../../utils/helper";
import ProteinImage from "./proteinImage";
import LoadingButton from "../../components/loading";

const AboutTarget = ({
  data,
  targetDetailsError,
  targetDetailsLoading,
  description,
  isRNA
}) => {
  const taxonomy = convertObjectToArray(data?.taxonomy) || [];

const synonymsData = isRNA ? data?.summary_and_characteristics?.Synonyms?.data
:data?.summary_and_characteristics?.Synonyms?.[
    "UniProt Synonyms"
  ];
  // Function to format description text
  const formatDescription = (text) => {
    if (!text) return "";

    // Find all “Inhibits ...” occurrences
    const inhibitsSentences = text.match(/Inhibits peroxisomal division when overexpressed\.?/g);

    if (inhibitsSentences && inhibitsSentences.length >= 2) {
      // Remove all inhibits sentences from the main text
      let main = text.replace(/Inhibits peroxisomal division when overexpressed\.?/g, "").trim();

      // Append prefixed inhibited lines with line breaks
      main += `\n[Isoform 1]: ${inhibitsSentences[inhibitsSentences.length - 2]}\n[Isoform 4]: ${inhibitsSentences[inhibitsSentences.length - 1]}`;
      return main;
    }

    return text;
  };

  return (
    <section id="introduction">
      <article id="target-description" className={`mt-8 px-[5vw] ${isRNA ? 'min-h-[50vh]' : 'min-h-[80vh]'}`}>
        <h1 className="text-3xl mb-2 font-semibold ">Description</h1>
        <p className="font-medium">
          This section provides a description of the biological function of the
          target.
        </p>
        {targetDetailsLoading && <LoadingButton />}
        {targetDetailsError && (
          <div className="ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center">
            <Empty />
          </div>
        )}

        {data && (
          <>
            <div>
              {!isRNA &&<span>
                Uniprot ID:{" "}
                <span className="text-sky-800">
                  {data.target_details?.uniprot_id}
                </span>{" "}
                |{" "}
              </span>}
              <span>
                ENSGID:{" "}
                <span className="text-sky-800">
                  {isRNA ? data?.ensembl_id:data.target_details?.ensembl_id}
                </span>
              </span>
            </div>
            <div className="flex gap-32 mt-3">
              <div className="flex-1 ">
                <h2 className="text-lg font-medium subHeading">
                  Function descriptions
                </h2>
                {/* Render with newlines */}
                <p className="text-justify whitespace-pre-line">{formatDescription(description)}</p>

                <h2 className="text-lg font-medium mb-2 mt-10 subHeading">
                  {isRNA ? "Synonyms":"Synonyms (from UniProt)"}
                </h2>
                <div className="flex flex-wrap gap-2">
                  {synonymsData?.map((synonym, synIndex) => (
                    
                    <Tooltip
                      title="Synonym"
                      key={synIndex}
                      overlayClassName="custom-tooltip"
                      color="#fff"
                    >
                      <div className="px-3 py-1 bg-blue-200 rounded-full text-sm text-gray-700 cursor-pointer">
                        {synonym}
                      </div>
                    </Tooltip>
                  ))}
                </div>
              </div>

             
                {data && !isRNA &&(
                   <div className="flex-1 mt-[-32px]">
                  <ProteinImage uniprot={data?.target_details?.uniprot_id} />
              </div>
                )}
               

            </div>
          </>
        )}
      </article>

      <article id="taxonomy" className="mt-12 px-[5vw] bg-gray-50 py-20">
        <h1 className="text-3xl font-semibold">Taxonomy</h1>
        <p className=" font-medium mt-2">
          This section provides an identifier for the target unique to an
          organism alongside its taxonomy.
        </p>

        {targetDetailsError ? (
          <div className="ag-theme-quartz mt-4 h-[80vh] max-h-[180px] flex items-center justify-center">
            <Empty />
          </div>
        ) : !targetDetailsError && !targetDetailsLoading && !data ? (
          <div className="h-[40vh] flex items-center justify-center">
            <Empty description="No data available" />
          </div>
        ) : (
          <div className="ag-theme-quartz mt-4 h-[80vh] max-h-[180px]">
            <AgGridReact
              defaultColDef={{
                flex: 1,
                headerClass: "font-semibold",
                autoHeight: true,
                wrapText: true,
                cellStyle: { whiteSpace: "normal", lineHeight: "20px" },
              }}
              columnDefs={[
                { field: "field" },
                {
                  field: "value",
                  cellRenderer: (params) => {
                    if (params.data.field === "Taxonomic Lineage") {
                      const arr = params?.value;
                      return arr.map((link, index) => (
                        <span key={index}>
                          <a
                            target="_blank"
                            href={`https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?name=${link}`}
                          >
                            {link}{" "}
                          </a>{" "}
                          {index < arr.length - 1 && " > "}
                        </span>
                      ));
                    } else if (params.data.field === "Taxonomic Identifier") {
                      return (
                        <a
                          target="_blank"
                          href={`https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=${params.value}`}
                        >
                          {params.value}
                        </a>
                      );
                    }
                    return params.value;
                  },
                },
              ]}
              rowData={data ? taxonomy : null}
              enableRangeSelection={true}
              enableCellTextSelection={true}
            />
          </div>
        )}
      </article>
    </section>
  );
};

export default AboutTarget;
