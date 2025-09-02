
import { Divider, Button, Typography } from 'antd';

const { Text } = Typography;

const LoginFooter = () => (
    <>
        <Divider className="border-blue-200" />
        <div className="text-center">
            <Text type="secondary" className="text-sm block mb-1 text-blue-600">Having problems logging in?</Text>
            <Button type="link" onClick={() => window.open('https://www.aganitha.ai/company/contact/', '_blank')} className="text-blue-600 hover:text-blue-800">Contact us</Button>
        </div>
    </>
);

export default LoginFooter;
