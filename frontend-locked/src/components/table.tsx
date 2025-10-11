import React, { useState, useEffect, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { Empty } from "antd";
import LoadingButton from "./loading";

const AutoSizingAgGrid = ({
  columnDefs,
  rowData,
  rowHeight = 30,
  paginationPageSize = 20,
}) => {
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Memoize default column definitions to prevent unnecessary re-renders
  const defaultColDef = useMemo(
    () => ({
      filter: true,
      floatingFilter: true,
      wrapHeaderText: true,
      flex: 1,
      minWidth: 150,
      autoHeaderHeight: true,
      autoHeight: true,
      sortable: true,
      wrapText: true,
      cellStyle: {
        whiteSpace: "normal",
        lineHeight: "20px",
      },
    }),
    []
  );

  // Manage loading state
  useEffect(() => {
    if (rowData.length > 0) {
      const loadingTimeout = setTimeout(() => {
        setIsLoading(false);
      }, 500);

      return () => clearTimeout(loadingTimeout);
    } else {
      setIsLoading(false);
    }
  }, [rowData]);

  // Calculate and set grid height

  // Render loading state
  if (isLoading) {
    return <LoadingButton />;
  }

  // Render empty state
  if (rowData.length === 0) {
    return (
      <div className="h-[40vh] flex items-center justify-center">
        <Empty description="No data available" />
      </div>
    );
  }

  return (
    <div className={`ag-theme-quartz ${rowData.length > 10 && "h-[70vh]"}`}>
      <AgGridReact
        columnDefs={columnDefs}
        rowData={rowData}
        defaultColDef={defaultColDef}
        rowHeight={rowHeight}
        pagination={true}
        paginationPageSize={paginationPageSize}
        // Removed commented-out headerHeight
        domLayout={rowData && rowData?.length <= 10 ? "autoHeight" : "normal"}
        enableRangeSelection={true}
        enableCellTextSelection={true}
        suppressColumnVirtualisation={true}
        suppressRowVirtualisation={true}
      />
    </div>
  );
};

export default React.memo(AutoSizingAgGrid);
