import { useState,useEffect } from "react";
import { ArrowDownOutlined, ArrowUpOutlined, InfoCircleOutlined } from "@ant-design/icons";
import { Tooltip } from "antd";
const CustomHeader = (props) => {
    const { displayName,title } = props;
    const [sortState, setSortState] = useState(null); // null, 'asc', or 'desc'
  
    const onSortRequested = () => {
      // Toggle between ascending, descending, and no sort
      let newSortState;
      if (!sortState) {
        newSortState = "asc";
      } else if (sortState === "asc") {
        newSortState = "desc";
      } else {
        newSortState = null;
      }
  
      setSortState(newSortState);
  
      // Call the sort method from AG Grid
      if (newSortState === null) {
        props.setSort(null);
      } else {
        props.setSort(newSortState);
      }
    };
  
    // Initialize sort state when component mounts
    useEffect(() => {
      // Check if column is already sorted
      const currentSort = props.column.getSort();
      if (currentSort) {
        setSortState(currentSort);
      }
  
      // Listen for sort changes
      const onSortChanged = () => {
        const currentSort = props.column.getSort();
        setSortState(currentSort || null);
      };
  
      // Modern AG Grid uses events differently
      props.api.addEventListener("sortChanged", onSortChanged);
  
      return () => {
        props.api.removeEventListener("sortChanged", onSortChanged);
      };
    }, []);
  
    return (
      <div
        onClick={onSortRequested}
        className="custom-header-cell"
        style={{ cursor: "pointer" }}
      >
        <span>{displayName}</span>
        <Tooltip
          // overlayClassName="custom-tooltip"
          color="black"
          title={title}
          style={{ maxWidth: "350px" }}
        >
          <InfoCircleOutlined className="text-base cursor-pointer ml-1 align-middle" />
        </Tooltip>
  
        {/* Sort indicator */}
        {sortState && (
          <span className=" ml-2">
            {sortState === "asc" ?<ArrowUpOutlined className="h-5 text-black-800"/> : <ArrowDownOutlined className="h-5" />}
          </span>
        )}
      </div>
    );
  };

  export default CustomHeader;