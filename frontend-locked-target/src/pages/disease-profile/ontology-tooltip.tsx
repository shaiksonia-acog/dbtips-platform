import React from "react";
import { Tooltip as AntdTooltip } from "antd";
// import "./OntologyTooltip.css"; // Import your custom CSS file

interface OntologyTooltipProps {
    style?: React.CSSProperties; // Type for inline styles
    children: React.ReactNode;
    title: React.ReactNode; // Can be string or React node
    placement?: "top" | "bottom" | "left" | "right"; // Define possible placements
}

const OntologyTooltip: React.FC<OntologyTooltipProps> = ({
    children,
    title,
    placement = "top",
}) => {

    return (
        <AntdTooltip
            placement={placement}
            overlayClassName="custom-tooltip"
            title={title}
            color="#fff"
        >
            {children}
        </AntdTooltip>
    );
};

export default OntologyTooltip;
