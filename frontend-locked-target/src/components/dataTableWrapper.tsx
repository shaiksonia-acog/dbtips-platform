import React, { useMemo, useState, ReactNode } from "react";
import { Empty } from "antd";
import Table from "./table";
import LoadingButton from "./loading";
import ColumnSelector from "./columnFilter";
import ExportButton from "./exportButton";

type ColumnDef = {
  field: string;
  headerName?: string;
  valueFormatter?: (params: any) => string | number;
  cellRenderer?: (params: any) => React.ReactNode;
};

type ExportOptions = {
  indications: string[];
  endpoint: string;
  fileName: string;
};

interface DataTableWrapperProps<T> {
  isLoading: boolean;
  error: unknown;
  data: T[];
  filterData?: T[]; // if filtered outside
  allColumns: ColumnDef[];
  defaultColumns: string[];
  exportOptions?: ExportOptions;
  filterComponent?: ReactNode;
  
}

const DataTableWrapper = <T,>({
  isLoading,
  error,
  data,
  filterData,
  allColumns,
  defaultColumns,
  exportOptions,
  filterComponent,
 
}: DataTableWrapperProps<T>): JSX.Element => {
  const [selectedColumns, setSelectedColumns] = useState<string[]>(defaultColumns);

  const visibleColumns = useMemo(() => {
    return allColumns.filter((col) => selectedColumns.includes(col.field));
  }, [allColumns, selectedColumns]);

  if (isLoading) return <LoadingButton />;

  if (error)
    return (
      <div className="h-[50vh] max-h-[280px] flex items-center justify-center">
        <Empty description={`${error}`} />
      </div>
    );

  if (!data || data.length === 0)
    return (
      <div className="h-[50vh] max-h-[280px] flex items-center justify-center">
        <Empty description="No data available" />
      </div>
    );

  return (
    <div>
     

      <div className="my-4 flex justify-between">
        {filterComponent && filterComponent}

        <div className="flex gap-2">
          <ColumnSelector
            allColumns={allColumns}
            defaultSelectedColumns={selectedColumns}
            onChange={setSelectedColumns}
          />
          {exportOptions && <ExportButton {...exportOptions} />}
        </div>
      </div>

      <Table columnDefs={visibleColumns} rowData={filterData ?? data} />
    </div>
  );
};

export default DataTableWrapper;
