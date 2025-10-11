import { useState,useEffect } from "react";
import { InfoCircleOutlined } from "@ant-design/icons";
import { Tooltip } from "antd";
const CustomHeader = (props) => {
    const { displayName } = props;
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
          overlayClassName="custom-tooltip"
          color="#fff"
          title={`Powered by LLM`}
          overlayStyle={{ maxWidth: "350px" }}
        >
          <InfoCircleOutlined className="text-base cursor-pointer ml-1 align-middle" />
        </Tooltip>
  
        {/* Sort indicator */}
        {sortState && (
          <span className="sort-indicator ml-1">
            {sortState === "asc" ? "↑" : "↓"}
          </span>
        )}
      </div>
    );
  };

  export default CustomHeader;