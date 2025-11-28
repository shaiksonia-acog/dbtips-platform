import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
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
  const gridRef = useRef(null);

  const memoizedColumnDefs = useMemo(() => columnDefs, [columnDefs]);

  const memoizedRowData = useMemo(() => rowData, [rowData]);

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

  // Memoize grid height calculation
  const gridHeight = useMemo(
    () => (memoizedRowData.length > 10 ? "h-[70vh]" : ""),
    [memoizedRowData.length]
  );

  // Memoize domLayout calculation
  const domLayout = useMemo(
    () => (memoizedRowData.length <= 10 ? "autoHeight" : "normal"),
    [memoizedRowData.length]
  );

  // Memoize isEmpty check
  const isEmpty = useMemo(
    () => memoizedRowData.length === 0,
    [memoizedRowData.length]
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
  }, [rowData.length]); 
  // Callback for grid ready event
  const onGridReady = useCallback((params) => {
    // Store grid API reference if needed for future operations
    gridRef.current = params.api;
  }, []);

  // Callback for first data rendered


  if (isLoading) {
    return <LoadingButton />;
  }

  if (isEmpty) {
    return (
      <div className="h-[40vh] flex items-center justify-center">
        <Empty description="No data available" />
      </div>
    );
  }

  return (
    <div className={`ag-theme-quartz ${gridHeight}`}>
      <AgGridReact
        ref={gridRef}
        columnDefs={memoizedColumnDefs}
        rowData={memoizedRowData}
        defaultColDef={defaultColDef}
        rowHeight={rowHeight}
        pagination={true}
        paginationPageSize={paginationPageSize}
        domLayout={domLayout}
        enableCellTextSelection={true}
        onGridReady={onGridReady}
      
        suppressMovableColumns={true} // Disable column moving if not needed
        suppressDragLeaveHidesColumns={true}
        rowBuffer={10} // Number of rows to render outside viewport
        debounceVerticalScrollbar={true}
      />
    </div>
  );
};

export default React.memo(AutoSizingAgGrid);