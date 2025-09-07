import { useQuery } from 'react-query';
import { Badge,  } from 'antd';
// import { fetchData } from '../utils/fetchData';
import { BellOutlined } from '@ant-design/icons';

const fetchData = async () => {
  const response = await fetch(`${import.meta.env.VITE_API_URI}/dossier/progression-tracker-dashboard/`);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return response.json(); // Return the JSON response
};
const Notification = ({ data }) => {



  // Fetch the notification data when the dropdown is visible
  const { data:apiData } = useQuery(['posts'], fetchData,
    {
      enabled:!!data
    }
  );
 console.log("data", apiData)
  
  const getBadgeCount = () => {
    if (!apiData || !apiData["processing"]) return 0;
    return apiData["processing"].length;
  };
  console.log("getBadgeCount", apiData?.submitted.length)
  return (
    <div>
      
        <div  className='cursor-pointer'>
          <Badge count={getBadgeCount()}>
            <BellOutlined style={{ fontSize: '20px', color: '#08c' }} />
          </Badge>
        </div>
    
    </div>
  );
};

export default Notification;