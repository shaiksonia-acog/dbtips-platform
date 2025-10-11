import { AgGridReact } from "ag-grid-react";
import { fetchData } from "../../utils/fetchData";
import { useQuery } from "react-query";
import { Empty } from "antd";
import LoadingButton from "../../components/loading";
const SubCellularLocation = ({ target }) => {
  // console.log('herrrrrr');
  // console.log(target, indications);
  const payload = {
    target: target,
  };

  const {
    data: targetSubCellularData,
    error: targetSubCellularError,
    isLoading: targetSubCellularLoading,
  } = useQuery(
    ["targetSubCellular", payload],
    () => fetchData(payload, "/target-profile/subcellular/"),
    {
      enabled: !!target,
    }
  );
  return (
    <section
      id="sub-cellular-location"
      className="mt-12 px-[5vw] bg-gray-50 py-20"
    >
      <h1 className="text-3xl font-semibold">Subcellular localization</h1>
      <p className="mt-2  font-medium">
        This section describes the location and the topology of the mature
        protein in the cell. It also highlights each non-membrane and
        membrane-spanning region of a protein which helps in tailored drug
        design.
      </p>

      {!targetSubCellularLoading &&
        !targetSubCellularError &&
        targetSubCellularData?.subcellular_locations?.length > 0 && (
          <div className="mt-2 text-left  max-w-md">
            {targetSubCellularData?.subcellular_locations.map(
              (location, index) => (
                <p key={index}>
                  <a
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline"
                    href={`https://www.uniprot.org/locations/${location.location.id}`}
                  >
                    {location.location.value}
                  </a>{" "}
                  {location.topology?.value}
                </p>
              )
            )}
          </div>
        )}

      {targetSubCellularError && (
        <div className="ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center">
          <Empty />
        </div>
      )}
      {targetSubCellularLoading && <LoadingButton />}
      {!targetSubCellularLoading &&
        !targetSubCellularError &&
        !targetSubCellularData?.subcellular.length &&
        !targetSubCellularData?.subcellular_locations?.length && (
          <div className="ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center">
            <Empty description="No data available " />
          </div>
        )}
      {!targetSubCellularLoading &&
        !targetSubCellularError &&
        (targetSubCellularData?.subcellular.length ? (
          <div className="ag-theme-quartz mt-4 h-[80vh] max-h-[280px]">
            <AgGridReact
              defaultColDef={{
                minWidth: 100,
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
                { field: "Type" },
                { field: "Positions" },
                {
                  field: "Description",
                  cellRenderer: (params) => (
                    <a href={params.data["Description Link"]} target="_blank">
                      {params.value}
                    </a>
                  ),
                },
                {
                  field: "Blast Link",
                  cellRenderer: (params) => (
                    <a target="_blank" href={params.value}>
                      {params.value}
                    </a>
                  ),
                },
              ]}
              rowData={targetSubCellularData.subcellular}
              pagination={true}
              enableRangeSelection={true}
              enableCellTextSelection={true}
            />
          </div>
        ) : (
          <div></div>
        ))}
    </section>
  );
};

export default SubCellularLocation;
