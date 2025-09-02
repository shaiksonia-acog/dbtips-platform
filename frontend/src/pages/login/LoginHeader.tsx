
import { Typography } from 'antd';
import Logo from './Logo';

const { Title, Text } = Typography;

const LoginHeader = () => (
    <>
        <Logo />
        <Title level={2} className="text-center mb-2 text-blue-800">Welcome To Aganitha</Title>
        <Text type="secondary" className="block text-center mb-6 text-blue-600">Sign in to your account</Text>
    </>
);

export default LoginHeader;
