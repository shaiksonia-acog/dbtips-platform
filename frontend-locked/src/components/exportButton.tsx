import { useState } from 'react';
import { useQuery } from "react-query";
import { Button } from "antd";
import { FileExcelOutlined } from "@ant-design/icons";
import { fetchData } from '../utils/fetchData';
const YourComponent = ({ indications=[], endpoint, fileName, target="",disabled=false }) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const downloadExcel = async () => {
    try {
      setIsDownloading(true);
      const payload = {
        endpoint: endpoint,
        diseases: indications,
        target:target
      };
      

      // Use the shared fetchData function with the export endpoint
      const blob = await fetchData(payload, "/export");
      // Create a blob from the response
      const blobObject = new Blob([blob], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      
      // Create download link
      const url = window.URL.createObjectURL(blobObject);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${target}-${fileName}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed:", error);

    } finally {
      setIsDownloading(false);
    }
  };

  const { refetch } = useQuery({
    queryKey: ["downloadExcel", indications, endpoint],
    queryFn: downloadExcel,
    enabled: false,
    
  });

  const handleDownload = () => {
    refetch();
  };

  return (
    <div>
      <Button
        onClick={handleDownload}
        type="primary"
        icon={<FileExcelOutlined className="align-middle text-xl" />}
        loading={isDownloading}
        disabled={disabled}
      >
        Export
      </Button>
    </div>
  );
};

export default YourComponent;